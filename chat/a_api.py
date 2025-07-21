# chat/api.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Conversation, Message
from .services.dialogue_manager import DialogueManager
from .services.nlp_processor import NLPProcessor


class ChatViewSet(viewsets.ViewSet):
    processor = NLPProcessor()
    manager = DialogueManager()

    @action(detail=False, methods=['post'])
    def chat(self, request):
        user = request.user
        text = request.data.get('text', '')

        # NLP处理
        nlp_result = self.processor.process_input(text)

        # 对话管理
        response = self.manager.process_message(user, {
            'text': text,
            'nlp_result': nlp_result
        })

        # 保存对话记录
        conv = Conversation.objects.create(
            user=user,
            current_state=response['state'],
            context=response['context']
        )
        Message.objects.create(
            conversation=conv,
            message_type='user',
            content=text,
            structured_data=nlp_result
        )

        return Response(response)

    import random
    import logging

    # 设置日志
    logging.basicConfig(
        filename='response_generator.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    class ResponseGenerator:
        """
        负责生成对话响应的类
        可以根据不同场景生成自然流畅的回复
        """

        def __init__(self):
            logging.info("初始化ResponseGenerator")

        def generate_greeting(self, username=None):
            """生成问候语"""
            greetings = [
                f"你好{f'，{username}' if username else ''}！欢迎使用我们的智能购物助手。请告诉我你想要找什么样的产品？",
                f"嗨{f'，{username}' if username else ''}！我是你的购物顾问。你有什么需求我可以帮你解决？",
                f"你好{f'，{username}' if username else ''}！我可以帮你推荐合适的商品。你最近在找什么产品吗？"
            ]
            selected = random.choice(greetings)
            logging.info(f"生成问候: {selected}")
            return selected

        def generate_collecting_response(self):
            """生成收集需求的回复"""
            responses = [
                "请告诉我你感兴趣的产品类型或品牌，这样我能更好地为你推荐。",
                "你对什么类型的产品感兴趣？有特定的品牌偏好吗？",
                "能详细描述一下你要找的产品吗？比如用途、预算或者特定功能。"
            ]
            selected = random.choice(responses)
            logging.info(f"生成收集需求回复: {selected}")
            return selected

        def generate_collecting_with_entities_response(self, entities):
            """生成针对特定实体的收集需求回复"""
            if not entities:
                return self.generate_collecting_response()

            entity_text = "、".join(entities)
            responses = [
                f"我注意到你提到了{entity_text}。你对这些产品有什么具体要求吗？比如价格区间或者特定功能？",
                f"关于{entity_text}，你有什么特别关注的点吗？比如性能、外观或者价格？",
                f"好的，你想要了解{entity_text}。你更关注哪些方面的特性呢？"
            ]
            selected = random.choice(responses)
            logging.info(f"生成带实体收集需求回复: {selected}")
            return selected

        def generate_clarifying_response(self, preferences):
            """生成澄清需求的回复"""
            # 根据用户之前的偏好生成澄清性问题
            if not preferences:
                return self.generate_collecting_response()

            # 分析用户偏好
            intents = [p.get('intent') for p in preferences if 'intent' in p]
            entities = []
            for p in preferences:
                if 'entities' in p and p['entities']:
                    entities.extend(p['entities'])
            entities = list(set(entities))

            if 'recommend' in intents and entities:
                responses = [
                    f"我看到你对{entities[0]}感兴趣。你更关注价格还是性能呢？",
                    f"关于{entities[0]}，你有什么价格范围的考虑吗？",
                    f"你对{entities[0]}有什么特别的需求或功能要求吗？"
                ]
            elif 'ask_info' in intents and entities:
                responses = [
                    f"你想了解{entities[0]}的什么具体信息？价格、性能还是其他方面？",
                    f"关于{entities[0]}，你最关心哪方面的参数或特性？",
                    f"你想知道{entities[0]}的哪些详细信息？"
                ]
            else:
                responses = [
                    "你能具体说说你对什么类型的产品感兴趣吗？",
                    "请告诉我你想找什么样的产品，或者有什么具体的品牌偏好？",
                    "你对什么价位的产品感兴趣？或者有什么功能需求？"
                ]

            selected = random.choice(responses)
            logging.info(f"生成澄清需求回复: {selected}")
            return selected

        def generate_recommendation_response(self, product_names, entities, preferences):
            """生成推荐产品的回复"""
            if not product_names:
                return self.generate_no_recommendation_response()

            # 提取关键信息
            product_text = "、".join(product_names)

            # 根据实体和偏好生成个性化推荐语
            if entities:
                entity_text = "、".join(entities[:2])  # 取前两个实体
                intros = [
                    f"根据你对{entity_text}的兴趣，我为你精选了以下产品：{product_text}。",
                    f"考虑到你提到的{entity_text}，我推荐这些产品：{product_text}。",
                    f"基于你对{entity_text}的需求，这些产品可能适合你：{product_text}。"
                ]
            else:
                intros = [
                    f"根据你的需求，我推荐以下产品：{product_text}。",
                    f"这些产品可能符合你的期望：{product_text}。",
                    f"我精选了这些产品给你：{product_text}。"
                ]

            outros = [
                "你对这些推荐有什么看法？或者需要了解更多细节？",
                "这些推荐符合你的需求吗？你想了解其中某个产品的更多信息吗？",
                "你觉得这些推荐怎么样？需要我调整一下吗？"
            ]

            selected = f"{random.choice(intros)} {random.choice(outros)}"
            logging.info(f"生成推荐回复: {selected}")
            return selected

        def generate_no_recommendation_response(self):
            """生成无推荐结果的回复"""
            responses = [
                "抱歉，我没有找到符合你需求的产品。能请你提供更多具体信息吗？",
                "目前没有找到合适的推荐。你能告诉我更多关于你想要的产品特性吗？",
                "很遗憾，我没能找到匹配的产品。你能描述一下你的预算或者其他要求吗？"
            ]
            selected = random.choice(responses)
            logging.info(f"生成无推荐回复: {selected}")
            return selected

        def generate_recommendation_error_response(self):
            """生成推荐出错的回复"""
            responses = [
                "抱歉，推荐过程中出现了问题。能请你重新描述一下你的需求吗？",
                "系统在处理你的需求时遇到了问题。你能再告诉我你在寻找什么样的产品吗？",
                "很抱歉，我无法完成推荐。请再次告诉我你的需求，我会重新为你推荐。"
            ]
            selected = random.choice(responses)
            logging.info(f"生成推荐错误回复: {selected}")
            return selected

        def generate_detail_response(self, entities, products):
            """生成详情查询的回复"""
            if not entities:
                return "你想了解哪个产品的详细信息？请告诉我具体的产品名称。"

            entity = entities[0]  # 取第一个实体作为查询对象

            # 模拟产品详情
            details = {
                "手机": "这款手机配备了高清屏幕、强大的处理器和长续航电池。屏幕尺寸6.5英寸，分辨率2400x1080，支持5G网络，电池容量4500mAh，快速充电支持，最新的操作系统。",
                "电脑": "这款电脑采用了最新的处理器、高速固态硬盘和高清显示屏。处理器为i7-12代，16GB内存，512GB SSD，15.6英寸显示屏，独立显卡，轻薄设计。",
                "平板": "这款平板电脑拥有10.9英寸全面屏设计，搭载高性能芯片和长续航电池。支持智能键盘和手写笔，适合办公和娱乐使用。",
                "耳机": "这款耳机采用了主动降噪技术、高品质音频和舒适的佩戴体验。电池续航时间长达30小时，支持快速充电，防水设计。",
                "相机": "这款相机具有高像素传感器、优秀的光学防抖和4K视频录制功能。支持WiFi连接，可直接分享照片到社交媒体。"
            }

            # 获取详情
            if entity in details:
                detail = details[entity]
            else:
                detail = f"{entity}配备了高品质的材料和先进的技术，具有出色的性能和用户体验。"

            responses = [
                f"关于{entity}的详细信息：{detail} 你对此还有其他疑问吗？",
                f"{entity}的主要特点是：{detail} 你想了解更多还是有其他需求？",
                f"以下是{entity}的详细规格：{detail} 这些信息对你有帮助吗？"
            ]

            selected = random.choice(responses)
            logging.info(f"生成详情查询回复: {selected}")
            return selected

        def generate_comparison_response(self, entities):
            """生成比较产品的回复"""
            if len(entities) < 2:
                return "你想比较哪些产品？请告诉我至少两个产品名称。"

            # 获取前两个实体
            entity1 = entities[0]
            entity2 = entities[1]

            # 模拟比较结果
            comparisons = {
                ("手机",
                 "平板"): f"手机相比平板更便携，适合随时通话和使用；而平板拥有更大的屏幕，适合看视频和阅读。手机一般电池续航时间较短，而平板续航时间更长。价格方面，手机的价格区间更广，而平板一般价格较高。",
                ("电脑",
                 "平板"): f"电脑性能更强大，适合复杂工作和游戏；而平板更轻便，续航更长，适合移动办公和娱乐。电脑功能更全面，而平板触控体验更好。价格方面，电脑一般价格更高。",
                ("手机",
                 "相机"): f"手机拍照方便随时可用，但专业性不如相机；相机拍摄质量更高，但便携性不如手机。手机多功能集合，而相机专注于拍摄。价格方面，高端手机价格可能高于入门级相机。"
            }

            # 获取比较结果
            key1 = (entity1, entity2)
            key2 = (entity2, entity1)

            if key1 in comparisons:
                comparison = comparisons[key1]
            elif key2 in comparisons:
                comparison = comparisons[key2].replace(entity2, "TEMP").replace(entity1, entity2).replace("TEMP",
                                                                                                          entity1)
            else:
                comparison = f"对比{entity1}和{entity2}，两者各有优势。{entity1}在某些方面表现更好，而{entity2}在其他方面可能更适合你。具体选择要根据你的实际需求来决定。"

            responses = [
                f"{comparison} 基于这些比较，你更倾向于哪一个？",
                f"{comparison} 希望这些信息能帮助你做出选择。你有其他问题吗？",
                f"{comparison} 考虑到这些因素，你的选择可能会更清晰。需要了解更多细节吗？"
            ]

            selected = random.choice(responses)
            logging.info(f"生成比较回复: {selected}")
            return selected

        def generate_positive_feedback_response(self):
            """生成积极反馈的回复"""
            responses = [
                "很高兴我的推荐对你有帮助！如果你有其他需求，随时告诉我。",
                "太好了！很开心你喜欢这些推荐。如果将来需要更多建议，欢迎再来咨询。",
                "谢谢你的肯定！希望这些推荐能真正满足你的需求。有其他问题随时问我。"
            ]
            selected = random.choice(responses)
            logging.info(