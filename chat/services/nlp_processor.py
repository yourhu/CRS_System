import os
import json
import torch
import logging
from transformers import BertTokenizer, BertForSequenceClassification
from django.conf import settings

logger = logging.getLogger(__name__)

# 定义意图和实体
INTENTS = ['recommend', 'ask_info', 'compare', 'unknown']
CATEGORIES = ['手机', '电脑', '平板', '耳机', '相机', '智能手表', '路由器', '游戏机', '音箱', '投影仪']
BRANDS = ['苹果', '华为', '小米', '索尼', '三星', 'OPPO', 'vivo', '联想', '戴尔', '惠普']
FEATURES = ['拍照', '游戏', '续航', '屏幕', '音质', '性能', '外观', '做工', '轻薄', '散热']
PRICE_RANGES = ['1000以下', '1000-2000', '2000-3000', '3000-5000', '5000-8000', '8000以上']


class NLPProcessor:
    """自然语言处理器，用于处理用户输入的文本信息"""

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load_model()

    def _load_model(self):
        """加载预训练的BERT模型"""
        try:
            model_dir = os.path.join(settings.BASE_DIR, 'chat', 'models', 'bert-finetuned')

            # 检查模型文件是否存在
            if os.path.exists(model_dir) and os.path.isdir(model_dir):
                self.tokenizer = BertTokenizer.from_pretrained(model_dir)
                self.model = BertForSequenceClassification.from_pretrained(model_dir).to(self.device)
                self.model.eval()
                logger.info("成功加载意图分类模型")
            else:
                # 如果没有找到微调模型，则使用默认的bert-base-chinese
                logger.warning("未找到微调模型，使用默认的BERT模型")
                self.tokenizer = BertTokenizer.from_pretrained('bert-base-chinese')
                self.model = BertForSequenceClassification.from_pretrained(
                    'bert-base-chinese',
                    num_labels=len(INTENTS)
                ).to(self.device)

        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            # 使用规则引擎作为备份
            self.model = None
            self.tokenizer = None

    def _extract_entities(self, text):
        """从文本中提取实体信息"""
        entities = {
            'category': None,
            'brand': None,
            'feature': None,
            'price_range': None,
            'price': None,
        }

        # 提取分类
        for category in CATEGORIES:
            if category in text:
                entities['category'] = category
                break

        # 提取品牌
        for brand in BRANDS:
            if brand in text:
                entities['brand'] = brand
                break

        # 提取特性
        for feature in FEATURES:
            if feature in text:
                entities['feature'] = feature
                break

        # 提取价格区间
        for price_range in PRICE_RANGES:
            if price_range in text:
                entities['price_range'] = price_range
                break

        # 简单的价格提取 - 查找数字+元或数字+"以下"/"左右"
        import re
        price_patterns = [
            r'(\d+)元',
            r'(\d+)块',
            r'(\d+)以下',
            r'(\d+)左右',
        ]

        for pattern in price_patterns:
            match = re.search(pattern, text)
            if match:
                price = int(match.group(1))
                entities['price'] = price
                break

        return entities

    def _rule_based_intent(self, text):
        """基于规则的意图识别（作为备用方案）"""
        recommend_keywords = ['推荐', '买', '购买', '好用', '值得', '选择']
        info_keywords = ['怎么样', '如何', '什么', '多少', '参数', '规格', '性能', '好吗']
        compare_keywords = ['对比', '比较', '和', '哪个好', '哪个更好', '区别', '不同', '差别']

        # 判断是否包含推荐关键词
        if any(keyword in text for keyword in recommend_keywords):
            return 'recommend'

        # 判断是否包含信息查询关键词
        elif any(keyword in text for keyword in info_keywords):
            # 还需要判断是否有比较的意图
            if any(keyword in text for keyword in compare_keywords):
                return 'compare'
            return 'ask_info'

        # 判断是否包含比较关键词
        elif any(keyword in text for keyword in compare_keywords):
            return 'compare'

        # 默认为未知意图
        else:
            return 'unknown'

    def process_input(self, text):
        """处理用户输入，返回意图和实体信息"""
        intent = 'unknown'
        confidence = 0.0

        # 使用BERT模型进行意图识别
        if self.model and self.tokenizer:
            try:
                inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128).to(
                    self.device)
                with torch.no_grad():
                    outputs = self.model(**inputs)

                logits = outputs.logits
                predicted_class = torch.argmax(logits, dim=1).item()
                confidence = torch.softmax(logits, dim=1)[0][predicted_class].item()
                intent = INTENTS[predicted_class]

                logger.info(f"BERT模型意图预测: {intent}, 置信度: {confidence:.4f}")

                # 如果置信度过低，使用规则引擎辅助判断
                if confidence < 0.7:
                    rule_intent = self._rule_based_intent(text)
                    # 如果BERT模型预测为unknown，采用规则引擎的结果
                    if intent == 'unknown':
                        intent = rule_intent
                        logger.info(f"BERT置信度低，切换到规则引擎结果: {intent}")
            except Exception as e:
                logger.error(f"模型预测失败: {e}")
                intent = self._rule_based_intent(text)
        else:
            # 如果模型加载失败，使用规则引擎
            intent = self._rule_based_intent(text)
            logger.info(f"使用规则引擎预测意图: {intent}")

        # 提取实体信息
        entities = self._extract_entities(text)

        # 返回处理结果
        result = {
            'intent': intent,
            'confidence': float(confidence),
            'entities': entities,
            'original_text': text
        }

        logger.info(f"NLP处理结果: {json.dumps(result, ensure_ascii=False)}")
        return result