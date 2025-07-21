import logging
import random
import numpy as np
from datetime import timedelta
from django.db.models import Q, Avg, Count, Sum, F, FloatField
from django.db.models.functions import Cast
from django.utils import timezone
from products.models import Product, Category
from orders.models import Order, OrderItem
from chat.models import Conversation, Recommendation

logger = logging.getLogger(__name__)


class Recommender:
    """
    增强型商品推荐系统
    结合内容过滤、协同过滤和规则过滤的混合推荐系统
    """

    def __init__(self):
        self.similarity_threshold = 0.3
        self.user_weight = 0.4  # 用户协同过滤权重
        self.content_weight = 0.3  # 内容过滤权重
        self.rule_weight = 0.3  # 规则过滤权重

    def get_recommendations(self, intent, entities, user=None, limit=5):
        """
        根据意图和实体生成推荐

        Args:
            intent: 用户意图 (recommend, ask_info, compare)
            entities: 实体信息字典
            user: 当前用户对象
            limit: 最大推荐商品数量

        Returns:
            dict: 包含推荐商品和相关信息的字典
        """
        try:
            if intent == 'recommend':
                return self._handle_recommendation(entities, user, limit)
            elif intent == 'ask_info':
                return self._handle_product_info(entities)
            elif intent == 'compare':
                return self._handle_product_comparison(entities)
            else:
                return {"products": [], "message": "无法理解您的需求，请尝试询问商品推荐或信息。"}
        except Exception as e:
            logger.error(f"推荐过程出错: {e}")
            return {"products": [], "message": "推荐系统暂时无法提供服务，请稍后再试。"}

    def _build_query(self, entities):
        """构建商品查询条件"""
        query = Q()

        # 按分类筛选
        if entities.get('category'):
            category_name = entities['category']
            try:
                # 查找匹配的分类
                categories = Category.objects.filter(name__icontains=category_name)
                if categories.exists():
                    category_ids = [c.id for c in categories]
                    query &= Q(category__in=category_ids)
            except Exception as e:
                logger.error(f"分类查询错误: {e}")

        # 按品牌筛选
        if entities.get('brand'):
            brand = entities['brand']
            # 假设商品名称或描述中包含品牌名称
            brand_query = Q(name__icontains=brand) | Q(specifications__brand__icontains=brand)
            query &= brand_query

        # 按价格筛选
        if entities.get('price'):
            price = entities['price']
            # 价格上下浮动20%
            min_price = price * 0.8
            max_price = price * 1.2
            query &= Q(price__gte=min_price) & Q(price__lte=max_price)
        elif entities.get('price_range'):
            price_range = entities['price_range']
            if price_range == '1000以下':
                query &= Q(price__lt=1000)
            elif price_range == '1000-2000':
                query &= Q(price__gte=1000) & Q(price__lte=2000)
            elif price_range == '2000-3000':
                query &= Q(price__gte=2000) & Q(price__lte=3000)
            elif price_range == '3000-5000':
                query &= Q(price__gte=3000) & Q(price__lte=5000)
            elif price_range == '5000-8000':
                query &= Q(price__gte=5000) & Q(price__lte=8000)
            elif price_range == '8000以上':
                query &= Q(price__gte=8000)

        # 按特性筛选
        if entities.get('feature'):
            feature = entities['feature']
            # 在描述或规格中查找特性
            feature_query = Q(description__icontains=feature) | Q(specifications__icontains=feature)
            query &= feature_query

        return query

    def _handle_recommendation(self, entities, user=None, limit=5):
        """
        处理商品推荐逻辑，结合多种推荐算法
        """
        try:
            # 基于规则过滤的候选商品
            rule_candidates = self._get_rule_based_candidates(entities, limit * 2)

            # 如果没有足够的候选商品，直接返回规则过滤结果
            if len(rule_candidates) < 2:
                if not rule_candidates:
                    return {
                        "products": [],
                        "message": "抱歉，没有找到符合条件的商品，请尝试其他条件。",
                        "algorithm": "rule_based"
                    }
                else:
                    message = self._generate_recommendation_message(entities)
                    return {
                        "products": rule_candidates[:limit],
                        "message": message,
                        "algorithm": "rule_based"
                    }

            # 为已登录用户提供个性化推荐
            if user and user.is_authenticated:
                # 基于用户协同过滤的推荐
                cf_candidates = self._get_collaborative_filtering_candidates(user, entities, limit * 2)

                # 基于内容的推荐
                content_candidates = self._get_content_based_candidates(user, entities, limit * 2)

                # 融合多种推荐结果
                final_products = self._hybrid_ranking(
                    rule_candidates,
                    cf_candidates,
                    content_candidates,
                    entities,
                    limit
                )

                algorithm = "hybrid"
            else:
                # 未登录用户只使用规则过滤和基于内容的推荐
                content_candidates = self._get_content_based_candidates(None, entities, limit * 2)

                # 简单融合规则过滤和基于内容的推荐
                final_products = self._simple_hybrid_ranking(
                    rule_candidates,
                    content_candidates,
                    entities,
                    limit
                )

                algorithm = "content_rule_hybrid"

            # 如果结果不足，补充热门商品
            if len(final_products) < limit:
                popular_products = self._get_popular_products(entities, limit - len(final_products))
                # 去重
                existing_ids = {p.id for p in final_products}
                for p in popular_products:
                    if p.id not in existing_ids:
                        final_products.append(p)
                        if len(final_products) >= limit:
                            break

            # 构建推荐回复消息
            message = self._generate_recommendation_message(entities)

            # 如果用户已登录，记录这次推荐
            if user and user.is_authenticated:
                try:
                    # 获取当前会话
                    current_conversation = Conversation.objects.filter(user=user).order_by('-created_at').first()

                    if current_conversation:
                        # 创建推荐记录
                        recommendation = Recommendation.objects.create(
                            conversation=current_conversation,
                            algorithm=algorithm
                        )
                        # 添加推荐的商品
                        recommendation.products.add(*[p.id for p in final_products])
                except Exception as e:
                    logger.error(f"记录推荐出错: {e}")

            return {
                "products": final_products,
                "message": message,
                "algorithm": algorithm
            }

        except Exception as e:
            logger.error(f"推荐查询错误: {e}")
            return {
                "products": [],
                "message": "推荐系统暂时出现问题，请稍后再试。",
                "algorithm": "error"
            }

    def _get_rule_based_candidates(self, entities, limit):
        """基于规则的过滤获取候选商品"""
        query = self._build_query(entities)

        # 查询符合条件的商品
        products = Product.objects.filter(query).filter(stock__gt=0).order_by('-created_at')[:limit]

        # 如果没有匹配的商品，尝试放宽条件
        if not products.exists() and entities.get('category'):
            # 只保留分类条件
            category_name = entities['category']
            categories = Category.objects.filter(name__icontains=category_name)
            if categories.exists():
                category_ids = [c.id for c in categories]
                products = Product.objects.filter(category__in=category_ids, stock__gt=0).order_by('-created_at')[
                           :limit]

        return list(products)

    def _get_collaborative_filtering_candidates(self, user, entities, limit):
        """基于用户协同过滤获取候选商品"""
        try:
            # 获取与当前用户行为相似的用户
            similar_users = self._find_similar_users(user, limit=20)

            if not similar_users:
                return []

            # 获取相似用户购买/查看过的商品
            # 优先考虑从订单中提取数据
            base_query = Q(order__user__in=similar_users, order__status__in=['paid', 'shipped', 'completed'])

            # 如果有分类过滤条件，应用它
            if entities.get('category'):
                category_name = entities['category']
                categories = Category.objects.filter(name__icontains=category_name)
                if categories.exists():
                    category_ids = [c.id for c in categories]
                    base_query &= Q(product__category__in=category_ids)

            # 如果有品牌过滤条件，应用它
            if entities.get('brand'):
                brand = entities['brand']
                base_query &= (Q(product__name__icontains=brand) |
                               Q(product__specifications__brand__icontains=brand))

            # 聚合计算商品得分（购买次数）
            product_scores = OrderItem.objects.filter(base_query).values(
                'product'
            ).annotate(
                score=Count('id')
            ).order_by('-score')[:limit]

            # 获取推荐的商品对象
            product_ids = [item['product'] for item in product_scores]
            recommended_products = list(Product.objects.filter(
                id__in=product_ids,
                stock__gt=0
            ))

            # 按得分排序
            product_id_to_score = {item['product']: item['score'] for item in product_scores}
            recommended_products.sort(key=lambda p: product_id_to_score.get(p.id, 0), reverse=True)

            return recommended_products

        except Exception as e:
            logger.error(f"协同过滤推荐错误: {e}")
            return []

    def _get_content_based_candidates(self, user, entities, limit):
        """基于内容的推荐获取候选商品"""
        try:
            base_query = Q(stock__gt=0)
            seed_products = []

            # 从用户历史购买或浏览记录中获取种子商品
            if user and user.is_authenticated:
                # 获取用户最近购买的商品
                recent_order_items = OrderItem.objects.filter(
                    order__user=user,
                    order__status__in=['paid', 'shipped', 'completed']
                ).order_by('-order__created_at')[:5]

                if recent_order_items.exists():
                    seed_products = [item.product for item in recent_order_items]

            # 如果没有种子商品，使用当前实体条件获取一些相关商品作为种子
            if not seed_products:
                query = self._build_query(entities)
                seed_products = list(Product.objects.filter(query).filter(stock__gt=0).order_by('-created_at')[:3])

            # 仍然没有种子商品，返回空结果
            if not seed_products:
                return []

            # 获取种子商品的分类和特性
            seed_categories = {product.category_id for product in seed_products}

            # 基于种子商品的特性查找相似商品
            content_based_candidates = []

            for seed_product in seed_products:
                # 在相同分类中查找相似商品
                similar_products = Product.objects.filter(
                    category=seed_product.category,
                    stock__gt=0
                ).exclude(
                    id=seed_product.id
                )

                # 如果有品牌偏好，应用它
                if entities.get('brand'):
                    brand = entities['brand']
                    similar_products = similar_products.filter(
                        Q(name__icontains=brand) | Q(specifications__brand__icontains=brand)
                    )

                # 应用价格过滤
                if entities.get('price'):
                    price = entities['price']
                    min_price = price * 0.8
                    max_price = price * 1.2
                    similar_products = similar_products.filter(price__gte=min_price, price__lte=max_price)
                elif entities.get('price_range'):
                    price_range = entities['price_range']
                    if price_range == '1000以下':
                        similar_products = similar_products.filter(price__lt=1000)
                    elif price_range == '1000-2000':
                        similar_products = similar_products.filter(price__gte=1000, price__lte=2000)
                    elif price_range == '2000-3000':
                        similar_products = similar_products.filter(price__gte=2000, price__lte=3000)
                    elif price_range == '3000-5000':
                        similar_products = similar_products.filter(price__gte=3000, price__lte=5000)
                    elif price_range == '5000-8000':
                        similar_products = similar_products.filter(price__gte=5000, price__lte=8000)
                    elif price_range == '8000以上':
                        similar_products = similar_products.filter(price__gte=8000)

                # 限制数量并添加到候选列表
                content_based_candidates.extend(list(similar_products[:limit // 2]))

            # 去重
            seen_ids = set()
            unique_candidates = []
            for product in content_based_candidates:
                if product.id not in seen_ids:
                    seen_ids.add(product.id)
                    unique_candidates.append(product)

            return unique_candidates[:limit]

        except Exception as e:
            logger.error(f"基于内容的推荐错误: {e}")
            return []

    def _find_similar_users(self, user, limit=20):
        """查找与目标用户购买行为相似的用户"""
        try:
            # 获取目标用户的购买历史
            user_purchases = OrderItem.objects.filter(
                order__user=user,
                order__status__in=['paid', 'shipped', 'completed']
            ).values_list('product_id', flat=True)

            user_product_set = set(user_purchases)

            # 如果用户没有购买历史，返回空
            if not user_product_set:
                return []

            # 查找有共同购买商品的用户
            similar_users_query = Order.objects.filter(
                status__in=['paid', 'shipped', 'completed'],
                items__product_id__in=user_product_set
            ).exclude(
                user=user
            ).values('user').annotate(
                common_products=Count('items__product_id', filter=Q(items__product_id__in=user_product_set)),
                total_products=Count('items__product_id', distinct=True)
            ).annotate(
                similarity=Cast('common_products', FloatField()) / Cast('total_products', FloatField())
            ).filter(
                similarity__gte=self.similarity_threshold
            ).order_by('-similarity')[:limit]

            similar_users = [item['user'] for item in similar_users_query]
            return similar_users

        except Exception as e:
            logger.error(f"查找相似用户错误: {e}")
            return []

    def _get_popular_products(self, entities, limit):
        """获取热门商品"""
        try:
            # 基础查询
            base_query = Q(stock__gt=0)

            # 应用分类过滤
            if entities.get('category'):
                category_name = entities['category']
                categories = Category.objects.filter(name__icontains=category_name)
                if categories.exists():
                    category_ids = [c.id for c in categories]
                    base_query &= Q(category__in=category_ids)

            # 计算热门商品（基于最近30天的销量）
            thirty_days_ago = timezone.now() - timedelta(days=30)

            popular_products = Product.objects.filter(base_query).annotate(
                sales=Sum('orderitem__quantity',
                          filter=Q(orderitem__order__created_at__gte=thirty_days_ago,
                                   orderitem__order__status__in=['paid', 'shipped', 'completed']))
            ).order_by('-sales', '-created_at')[:limit]

            return list(popular_products)

        except Exception as e:
            logger.error(f"获取热门商品错误: {e}")
            return []

    def _hybrid_ranking(self, rule_candidates, cf_candidates, content_candidates, entities, limit):
        """融合多种推荐结果，使用加权排名"""
        try:
            # 合并所有候选商品并去重
            all_candidates = {}

            # 给规则过滤的候选商品评分
            for i, product in enumerate(rule_candidates):
                score = (len(rule_candidates) - i) / len(rule_candidates) if rule_candidates else 0
                all_candidates[product.id] = {
                    'product': product,
                    'rule_score': score,
                    'cf_score': 0,
                    'content_score': 0
                }

            # 给协同过滤的候选商品评分
            for i, product in enumerate(cf_candidates):
                score = (len(cf_candidates) - i) / len(cf_candidates) if cf_candidates else 0
                if product.id in all_candidates:
                    all_candidates[product.id]['cf_score'] = score
                else:
                    all_candidates[product.id] = {
                        'product': product,
                        'rule_score': 0,
                        'cf_score': score,
                        'content_score': 0
                    }

            # 给基于内容的候选商品评分
            for i, product in enumerate(content_candidates):
                score = (len(content_candidates) - i) / len(content_candidates) if content_candidates else 0
                if product.id in all_candidates:
                    all_candidates[product.id]['content_score'] = score
                else:
                    all_candidates[product.id] = {
                        'product': product,
                        'rule_score': 0,
                        'cf_score': 0,
                        'content_score': score
                    }

            # 计算加权总分
            for product_id, data in all_candidates.items():
                data['total_score'] = (
                        self.rule_weight * data['rule_score'] +
                        self.user_weight * data['cf_score'] +
                        self.content_weight * data['content_score']
                )

            # 按总分排序
            ranked_candidates = sorted(
                all_candidates.values(),
                key=lambda x: x['total_score'],
                reverse=True
            )

            # 取前N个商品
            final_products = [item['product'] for item in ranked_candidates[:limit]]

            return final_products

        except Exception as e:
            logger.error(f"混合排序错误: {e}")
            # 如果混合排序失败，回退到规则过滤结果
            return rule_candidates[:limit]

    def _simple_hybrid_ranking(self, rule_candidates, content_candidates, entities, limit):
        """未登录用户的简单混合排名"""
        try:
            # 合并规则过滤和基于内容的推荐结果
            all_candidates = {}

            # 规则过滤结果评分
            for i, product in enumerate(rule_candidates):
                score = (len(rule_candidates) - i) / len(rule_candidates) if rule_candidates else 0
                all_candidates[product.id] = {
                    'product': product,
                    'rule_score': score,
                    'content_score': 0
                }

            # 基于内容的推荐评分
            for i, product in enumerate(content_candidates):
                score = (len(content_candidates) - i) / len(content_candidates) if content_candidates else 0
                if product.id in all_candidates:
                    all_candidates[product.id]['content_score'] = score
                else:
                    all_candidates[product.id] = {
                        'product': product,
                        'rule_score': 0,
                        'content_score': score
                    }

            # 计算加权总分
            simple_rule_weight = 0.6
            simple_content_weight = 0.4

            for product_id, data in all_candidates.items():
                data['total_score'] = (
                        simple_rule_weight * data['rule_score'] +
                        simple_content_weight * data['content_score']
                )

            # 按总分排序
            ranked_candidates = sorted(
                all_candidates.values(),
                key=lambda x: x['total_score'],
                reverse=True
            )

            # 取前N个商品
            final_products = [item['product'] for item in ranked_candidates[:limit]]

            return final_products

        except Exception as e:
            logger.error(f"简单混合排序错误: {e}")
            # 如果混合排序失败，回退到规则过滤结果
            return rule_candidates[:limit]

    def _generate_recommendation_message(self, entities):
        """根据实体生成推荐消息"""
        if entities.get('feature'):
            message = f"根据您对{entities['feature']}的需求，为您推荐以下商品："
        elif entities.get('brand'):
            message = f"为您推荐以下{entities['brand']}品牌的商品："
        elif entities.get('category'):
            message = f"为您推荐以下{entities['category']}商品："
        else:
            message = "根据您的需求，为您推荐以下商品："

        return message

    def _handle_product_info(self, entities):
        """处理商品信息查询逻辑"""
        query = self._build_query(entities)

        try:
            products = Product.objects.filter(query).filter(stock__gt=0).order_by('-created_at')[:3]

            if not products.exists():
                if entities.get('category') and entities.get('brand'):
                    return {"products": [],
                            "message": f"抱歉，暂时没有找到{entities['brand']}的{entities['category']}产品信息。"}
                elif entities.get('category'):
                    return {"products": [], "message": f"抱歉，暂时没有找到{entities['category']}产品信息。"}
                elif entities.get('brand'):
                    return {"products": [], "message": f"抱歉，暂时没有找到{entities['brand']}的产品信息。"}
                else:
                    return {"products": [], "message": "抱歉，没有找到相关产品信息。"}

            # 构建回复消息
            if entities.get('feature') and entities.get('category'):
                message = f"以下是{entities['category']}的{entities['feature']}相关信息："
            elif entities.get('brand') and entities.get('category'):
                message = f"以下是{entities['brand']}的{entities['category']}相关信息："
            elif entities.get('category'):
                message = f"以下是{entities['category']}的相关信息："
            else:
                message = "以下是您查询的产品信息："

            return {
                "products": list(products),
                "message": message,
                "algorithm": "info_query"
            }

        except Exception as e:
            logger.error(f"信息查询错误: {e}")
            return {
                "products": [],
                "message": "查询系统暂时出现问题，请稍后再试。",
                "algorithm": "error"
            }

    def _handle_product_comparison(self, entities):
        """处理商品比较逻辑"""
        query = self._build_query(entities)

        try:
            products = Product.objects.filter(query).filter(stock__gt=0).order_by('-created_at')[:5]

            if not products.exists():
                return {
                    "products": [],
                    "message": "抱歉，没有找到可比较的商品。",
                    "algorithm": "comparison"
                }

            # 如果只有一个品牌，则寻找同类别的其他品牌产品进行比较
            if entities.get('brand') and len(products) < 2:
                category_ids = [p.category_id for p in products]
                other_brand_products = Product.objects.filter(
                    category__in=category_ids,
                    stock__gt=0
                ).exclude(
                    Q(name__icontains=entities['brand']) | Q(specifications__brand__icontains=entities['brand'])
                ).order_by('-created_at')[:4]

                products = list(products) + list(other_brand_products)

            # 构建比较消息
            if entities.get('feature') and entities.get('category'):
                message = f"以下是{entities['category']}中{entities['feature']}表现的比较："
            elif entities.get('brand') and entities.get('category'):
                message = f"以下是{entities['brand']}与其他品牌{entities['category']}的比较："
            elif entities.get('category'):
                message = f"以下是{entities['category']}的品牌比较："
            else:
                message = "以下是相关产品的比较："

            return {
                "products": products,
                "message": message,
                "algorithm": "comparison",
                "comparison_feature": entities.get('feature')
            }

        except Exception as e:
            logger.error(f"比较查询错误: {e}")
            return {
                "products": [],
                "message": "比较系统暂时出现问题，请稍后再试。",
                "algorithm": "error"
            }