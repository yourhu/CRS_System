import json
import logging
from datetime import datetime
from .nlp_processor import NLPProcessor
from .recommender import Recommender
from ..models import Conversation, Message, Recommendation
from products.models import Product

logger = logging.getLogger(__name__)


class DialogueManager:
    """
    对话管理器，负责处理用户消息并管理对话状态

    功能包括：
    - 处理用户输入
    - 管理对话状态
    - 调用NLP处理器和推荐引擎
    - 生成系统回复
    """

    def __init__(self):
        self.nlp = NLPProcessor()
        self.recommender = Recommender()

    def process_message(self, user, message_data):
        """
        处理用户消息并返回系统回复

        Args:
            user: 当前用户对象
            message_data: 包含用户消息和NLP结果的字典

        Returns:
            dict: 包含系统回复和对话状态的字典
        """
        text = message_data.get('text', '')
        nlp_result = message_data.get('nlp_result')

        if not nlp_result:
            # 如果没有传入NLP结果，则处理原始文本
            nlp_result = self.nlp.process_input(text)

        # 获取或创建会话
        conversation = self._get_or_create_conversation(user)

        # 更新会话上下文
        self._update_context(conversation, nlp_result)

        # 获取并处理用户意图
        intent = nlp_result['intent']
        entities = nlp_result['entities']

        # 根据意图生成回复
        response = self._generate_response(conversation, intent, entities)

        # 更新会话状态
        new_state = self._determine_next_state(conversation.current_state, intent)

        # 记录本次推荐
        if 'products' in response and response['products'] and len(response['products']) > 0:
            algorithm = response.get('algorithm', 'unknown')
            recommendation = Recommendation.objects.create(
                conversation=conversation,
                algorithm=algorithm
            )
            # 添加推荐的商品
            for product in response['products']:
                recommendation.products.add(product)

        return {
            'response': response['message'] if isinstance(response, dict) and 'message' in response else response,
            'structured_data': self._prepare_structured_data(response),
            'state': new_state,
            'context': conversation.context
        }

    def _get_or_create_conversation(self, user):
        """获取当前活跃会话或创建新会话"""
        # 查找当前用户最近的未关闭会话
        active_conversation = Conversation.objects.filter(
            user=user,
            current_state__in=[
                Conversation.State.INIT,
                Conversation.State.COLLECTING,
                Conversation.State.RECOMMENDING
            ]
        ).order_by('-updated_at').first()

        if active_conversation:
            return active_conversation

        # 创建新会话
        return Conversation.objects.create(
            user=user,
            current_state=Conversation.State.INIT,
            context={}
        )

    def _update_context(self, conversation, nlp_result):
        """更新会话上下文"""
        context = conversation.context

        # 合并实体信息
        if 'entities' not in context:
            context['entities'] = {}

        # 更新实体信息，只添加有值的实体
        for key, value in nlp_result['entities'].items():
            if value:
                context['entities'][key] = value

        # 记录最近的意图
        context['last_intent'] = nlp_result['intent']
        context['last_message_time'] = datetime.now().isoformat()

        # 保存上下文
        conversation.context = context
        conversation.save()

    def _determine_next_state(self, current_state, intent):
        """确定下一个对话状态"""
        if current_state == Conversation.State.INIT:
            if intent in ['recommend', 'ask_info', 'compare']:
                return Conversation.State.COLLECTING
            return current_state

        elif current_state == Conversation.State.COLLECTING:
            if intent in ['recommend', 'compare']:
                return Conversation.State.RECOMMENDING
            return current_state

        elif current_state == Conversation.State.RECOMMENDING:
            if intent == 'unknown':
                return Conversation.State.FEEDBACK
            return current_state

        elif current_state == Conversation.State.FEEDBACK:
            if intent == 'unknown':
                return Conversation.State.CLOSED
            return Conversation.State.COLLECTING

        return current_state

    def _generate_response(self, conversation, intent, entities):
        """
        根据意图和实体生成系统回复

        Args:
            conversation: 当前会话对象
            intent: 用户意图
            entities: 实体信息

        Returns:
            dict: 回复信息，包含文本消息和结构化数据
        """
        try:
            # 合并会话中保存的实体信息
            context_entities = conversation.context.get('entities', {})
            merged_entities = {**context_entities, **entities}

            # 根据不同意图处理
            if intent == 'recommend':
                # 商品推荐
                return self.recommender.get_recommendations(
                    intent='recommend',
                    entities=merged_entities,
                    user=conversation.user
                )

            elif intent == 'ask_info':
                # 商品信息查询
                return self.recommender.get_recommendations(
                    intent='ask_info',
                    entities=merged_entities
                )

            elif intent == 'compare':
                # 商品比较
                return self.recommender.get_recommendations(
                    intent='compare',
                    entities=merged_entities
                )

            elif intent == 'unknown':
                # 处理未知意图
                last_intent = conversation.context.get('last_intent')

                if conversation.current_state == Conversation.State.RECOMMENDING:
                    return {
                        "message": "您对推荐的商品感觉如何？需要了解更多信息还是有其他需求？",
                        "products": []
                    }
                elif last_intent in ['recommend', 'ask_info', 'compare']:
                    return {
                        "message": "抱歉，我没有理解您的意思。您可以告诉我您想了解什么商品，或者需要什么样的推荐？",
                        "products": []
                    }
                else:
                    return {
                        "message": "您好！我是商品推荐助手，可以帮您推荐商品、查询商品信息或比较不同商品。请问您需要什么帮助？",
                        "products": []
                    }
            else:
                return {
                    "message": "抱歉，我暂时无法处理这个请求。请问您需要什么商品推荐或信息？",
                    "products": []
                }

        except Exception as e:
            logger.error(f"生成回复出错: {e}")
            return {
                "message": "抱歉，系统暂时出现了问题，请稍后再试。",
                "products": []
            }

    def _prepare_structured_data(self, response):
        """准备结构化的回复数据"""
        structured_data = {}

        # 添加商品信息
        if isinstance(response, dict) and 'products' in response and response['products']:
            products_data = []
            for product in response['products']:
                product_dict = {
                    'id': product.id,
                    'name': product.name,
                    'price': float(product.price),
                    'description': product.description,
                    'specifications': product.specifications,
                    'image': product.image.url if product.image else None,
                    'category': product.category.name,
                }
                products_data.append(product_dict)

            structured_data['products'] = products_data

            # 添加算法信息
            if 'algorithm' in response:
                structured_data['algorithm'] = response['algorithm']

            # 添加比较特性
            if 'comparison_feature' in response:
                structured_data['comparison_feature'] = response['comparison_feature']

        return structured_data if structured_data else None