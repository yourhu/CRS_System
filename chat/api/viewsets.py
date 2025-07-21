from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from chat.models import Conversation, Message, Recommendation
from chat.services.nlp_processor import NLPProcessor
from chat.services.dialogue_manager import  DialogueManager
from chat.services.recommender import  HybridRecommender
from chat.serializers import ConversationSerializer

class ChatViewSet(viewsets.ViewSet):
    processor = NLPProcessor()
    manager = DialogueManager()
    recommender = HybridRecommender()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 初始化推荐模型
        products = Product.objects.all()
        ratings = pd.DataFrame(list(
            OrderItem.objects.annotate(
                user_id=F('order__user_id'),
                product_id=F('product_id'),
                rating=Value(4.5, output_field=FloatField())
            ).values('user_id', 'product_id', 'rating')
        ))
        self.recommender.train_collaborative_filtering(ratings)
        self.recommender.train_content_based(products)

    @action(detail=False, methods=['post'])
    def chat(self, request):
        user = request.user
        text = request.data.get('text', '')

        # NLP 处理
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
        Message.objects.create(
            conversation=conv,
            message_type='system',
            content=response['response']
        )

        # 保存推荐结果（如果有）
        if response['state'] == 'recommending' and 'products' in response:
            rec = Recommendation.objects.create(
                conversation=conv,
                algorithm='hybrid'
            )
            rec.products.set(response['products'])

        serializer = ConversationSerializer(conv)
        return Response(serializer.data)