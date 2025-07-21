from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import json
import logging

from .models import Conversation, Message, Recommendation
from .services.nlp_processor import NLPProcessor
from .services.dialogue_manager import DialogueManager
from products.models import Product
from .serializers import ConversationSerializer

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class ChatView(View):
    def get(self, request):
        return render(request, 'chat/chat.html')

    def post(self, request):
        try:
            data = json.loads(request.body)
            text = data.get('text', '').strip()
            print("收到请求：", data)
            print("用户：", request.user)

            if not text:
                return JsonResponse({'error': '消息不能为空'}, status=400)

            # 获取或创建会话
            conversation, _ = Conversation.objects.get_or_create(
                user=request.user,
                current_state=Conversation.State.INIT,
                defaults={'context': {}},
            )

            # 创建用户消息
            Message.objects.create(
                conversation=conversation,
                message_type=Message.MessageType.USER_TEXT,
                content=text
            )

            # 处理消息
            nlp = NLPProcessor()
            nlp_result = nlp.process_input(text)

            dm = DialogueManager()
            response = dm.process_message(request.user, {'text': text, 'nlp_result': nlp_result})

            # 更新会话状态
            conversation.current_state = response['state']
            conversation.context = response.get('context', {})
            conversation.save()

            # 创建系统回复消息
            # 存储结构化数据
            system_message = Message.objects.create(
                conversation=conversation,
                message_type=Message.MessageType.SYSTEM_TEXT,
                content=response['response'],
                structured_data=response.get('structured_data')
            )

            # 如果有商品数据，为每个商品创建单独的消息
            products_data = []
            if response.get('structured_data') and response['structured_data'].get('products'):
                for product in response['structured_data']['products']:
                    products_data.append({
                        'id': product['id'],
                        'name': product['name'],
                        'price': product['price'],
                        'description': product['description'],
                        'image': product['image'],
                        'category': product['category']
                    })

            # 构建响应
            messages = []
            # 获取用户消息
            user_msg = Message.objects.filter(
                conversation=conversation,
                message_type=Message.MessageType.USER_TEXT
            ).last()

            if user_msg:
                messages.append({
                    'message_type': 'user',
                    'content': user_msg.content
                })

            # 添加系统回复
            messages.append({
                'message_type': 'system',
                'content': system_message.content
            })

            # 添加商品数据
            for product in products_data:
                messages.append({
                    'message_type': 'product',
                    'content': product['name'],
                    'structured_data': product
                })

            return JsonResponse({'messages': messages})
        except Exception as e:
            import traceback
            logger.error(f"Chat API error: {e}" + traceback.format_exc())
            return JsonResponse({'error': str(e), 'trace': traceback.format_exc()}, status=500)


@method_decorator(login_required, name='dispatch')
class ConversationHistoryView(View):
    def get(self, request):
        conversations = Conversation.objects.filter(user=request.user).prefetch_related('messages')
        history = []
        for conv in conversations:
            history.append({
                'id': conv.id,
                'messages': [
                    {
                        'message_type': msg.message_type,
                        'content': msg.content,
                        'structured_data': msg.structured_data
                    } for msg in conv.messages.all()
                ]
            })
        return JsonResponse(history, safe=False)