import os
import random
import pandas as pd
import torch
from transformers import BertTokenizer, BertForSequenceClassification, Trainer, TrainingArguments
from datasets import Dataset
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

# 禁用 Symlinks 警告
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

# 使用绝对路径保存模型
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MODEL_DIR = os.path.join(BASE_DIR, 'chat', 'models', 'bert-finetuned')
os.makedirs(MODEL_DIR, exist_ok=True)
print(f"模型将保存到: {MODEL_DIR}")

# 定义意图和实体
INTENTS = ['recommend', 'ask_info', 'compare', 'unknown']
CATEGORIES = ['手机', '电脑', '平板', '耳机', '相机', '智能手表', '路由器', '游戏机', '音箱', '投影仪']
BRANDS = ['苹果', '华为', '小米', '索尼', '三星', 'OPPO', 'vivo', '联想', '戴尔', '惠普']
FEATURES = ['拍照', '游戏', '续航', '屏幕', '音质', '性能', '外观', '做工', '轻薄', '散热']
PRICE_RANGES = ['1000以下', '1000-2000', '2000-3000', '3000-5000', '5000-8000', '8000以上']

# 文本模板
TEMPLATES = {
    'recommend': [
        "我想买{category}",
        "推荐一个{brand}的{category}",
        "有什么{feature}好的{category}吗",
        "给我推荐一款{category}",
        "我想买个{category}，有什么推荐",
        "推荐一款性价比高的{category}",
        "我想买{brand}的{category}，有什么推荐",
        "推荐一个适合{feature}的{category}",
        "有什么{category}推荐吗",
        "推荐一个{price_range}的{category}",
        "{category}哪款好",
        "有没有适合{feature}的{category}推荐",
        "帮我选一款{category}",
        "有什么好用的{category}",
        "我需要一个新{category}",
        "求推荐一款{brand}的{category}",
        "有没有便宜又好用的{category}",
        "最近有什么值得买的{category}",
        "{category}什么品牌比较好",
        "预算{price}元想买{category}",
    ],
    'ask_info': [
        "{category}有什么功能",
        "{brand}的{category}怎么样",
        "{category}的价格是多少",
        "{category}的{feature}好吗",
        "{category}的规格是什么",
        "{category}的保修期是多久",
        "{category}的重量是多少",
        "{category}的屏幕尺寸是多少",
        "{category}的电池容量是多少",
        "{category}的处理器是什么",
        "{brand}{category}多少钱",
        "{category}的参数是什么",
        "{category}支持快充吗",
        "{category}的摄像头怎么样",
        "{category}有什么颜色可选",
        "{brand}的{category}支持无线充电吗",
        "{category}的内存有多大",
        "{category}的存储空间有多大",
        "{category}的操作系统是什么",
        "{category}的售后怎么样",
    ],
    'compare': [
        "{category1}和{category2}哪个好",
        "{brand1}和{brand2}的{category}哪个好",
        "{category}中{feature}最好的是哪个",
        "{category}中性价比最高的是哪个",
        "{category}中{feature}最差的是哪个",
        "{brand1}{category}和{brand2}{category}比较",
        "{brand1}和{brand2}哪个{category}更好用",
        "同价位的{category}哪个更值得买",
        "{price_range}的{category}该选哪个品牌",
        "{brand1}{category}和{brand2}{category}有什么区别",
        "{category}性价比排行",
        "{feature}方面{brand1}和{brand2}的{category}哪个强",
        "{category}各品牌优缺点对比",
        "入门级{category}应该买哪个牌子",
        "高端{category}哪个最好",
        "{feature}需求买什么{category}好",
        "{price_range}预算买{brand1}还是{brand2}的{category}",
        "{category}跟{category2}功能对比",
        "学生用{category}推荐哪个牌子",
        "办公用{category}买什么好",
    ],
    'unknown': [
        "你好",
        "今天天气怎么样",
        "你是谁",
        "你会做什么",
        "你有什么功能",
        "你能帮我做什么",
        "谢谢你",
        "再见",
        "这个怎么用",
        "我不想买东西",
        "帮我查询订单",
        "怎么退货",
        "我想投诉",
        "优惠券怎么用",
        "积分如何兑换",
        "你们的客服电话是多少",
        "我想修改收货地址",
        "如何注册账号",
        "怎么修改密码",
        "物流信息查询",
    ]
}


def generate_training_data(num_samples=2000):
    """生成训练数据"""
    samples_per_intent = num_samples // len(INTENTS)
    data = []

    for intent in INTENTS:
        for _ in range(samples_per_intent):
            template = random.choice(TEMPLATES[intent])

            if intent == 'recommend':
                category = random.choice(CATEGORIES)
                brand = random.choice(BRANDS)
                feature = random.choice(FEATURES)
                price = random.randint(1000, 10000)
                price_range = random.choice(PRICE_RANGES)
                text = template.format(
                    category=category, brand=brand, feature=feature,
                    price=price, price_range=price_range
                )
            elif intent == 'ask_info':
                category = random.choice(CATEGORIES)
                brand = random.choice(BRANDS)
                feature = random.choice(FEATURES)
                text = template.format(category=category, brand=brand, feature=feature)
            elif intent == 'compare':
                category = random.choice(CATEGORIES)
                category1 = category
                category2 = random.choice([c for c in CATEGORIES if c != category])
                brand1 = random.choice(BRANDS)
                brand2 = random.choice([b for b in BRANDS if b != brand1])
                feature = random.choice(FEATURES)
                price_range = random.choice(PRICE_RANGES)
                text = template.format(
                    category=category, category1=category1, category2=category2,
                    brand1=brand1, brand2=brand2, feature=feature, price_range=price_range
                )
            else:  # unknown
                text = template

            # 添加一些随机变化以增加多样性
            if random.random() < 0.3 and intent != 'unknown':
                # 30%的概率添加一些口语化表达
                prefixes = ["请问", "麻烦问一下", "想知道", "帮我看看", "我想了解一下"]
                suffixes = ["谢谢", "谢谢你", "感谢", "可以吗", "怎么样"]

                if random.random() < 0.5:
                    text = f"{random.choice(prefixes)}{text}"
                else:
                    text = f"{text}{random.choice(suffixes)}"

            data.append({'text': text, 'intent': intent})

    # 随机打乱数据
    random.shuffle(data)
    return pd.DataFrame(data)


def compute_metrics(pred):
    """计算模型评估指标"""
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)
    precision, recall, f1, _ = precision_recall_fscore_support(labels, preds, average='weighted')
    acc = accuracy_score(labels, preds)
    return {
        'accuracy': acc,
        'f1': f1,
        'precision': precision,
        'recall': recall
    }


def train_intent_classifier(df, output_dir=MODEL_DIR, epochs=3):
    """训练意图分类模型"""
    # 加载数据
    dataset = Dataset.from_pandas(df)

    # 意图标签映射
    label_map = {intent: idx for idx, intent in enumerate(INTENTS)}
    print(f"标签映射: {label_map}")
    dataset = dataset.map(lambda x: {"labels": label_map[x["intent"]]})

    # 加载 tokenizer 和模型
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"使用设备: {device}")

    try:
        tokenizer = BertTokenizer.from_pretrained('bert-base-chinese')
        model = BertForSequenceClassification.from_pretrained('bert-base-chinese', num_labels=len(INTENTS)).to(device)
        print("成功加载基础模型")
    except Exception as e:
        print(f"加载模型失败: {e}")
        raise

    # 预处理数据
    def preprocess_function(examples):
        return tokenizer(examples['text'], truncation=True, padding='max_length', max_length=128)

    tokenized_dataset = dataset.map(preprocess_function, batched=True)
    split_dataset = tokenized_dataset.train_test_split(test_size=0.2)
    train_dataset = split_dataset['train']
    eval_dataset = split_dataset['test']

    print(f"训练集大小: {len(train_dataset)}, 测试集大小: {len(eval_dataset)}")

    # 设置训练参数
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir=os.path.join(output_dir, 'logs'),
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
    )

    # 定义 Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        compute_metrics=compute_metrics,
    )

    # 训练模型
    try:
        print("开始训练...")
        trainer.train()
        print("训练完成")

        # 评估模型
        eval_results = trainer.evaluate()
        print(f"评估结果: {eval_results}")
    except Exception as e:
        print(f"训练失败: {e}")
        raise

    # 保存模型和 tokenizer
    try:
        model.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)
        print(f"模型和 tokenizer 已保存到: {output_dir}")

        # 列出保存的文件
        saved_files = os.listdir(output_dir)
        print(f"保存的文件: {saved_files}")

        return model, tokenizer
    except Exception as e:
        print(f"保存失败: {e}")
        raise


def test_model(model, tokenizer, texts):
    """测试模型对给定文本的分类结果"""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    results = []
    for text in texts:
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128).to(device)
        with torch.no_grad():
            outputs = model(**inputs)

        logits = outputs.logits
        predicted_class = torch.argmax(logits, dim=1).item()
        confidence = torch.softmax(logits, dim=1)[0][predicted_class].item()
        predicted_intent = INTENTS[predicted_class]

        results.append({
            "text": text,
            "predicted_intent": predicted_intent,
            "confidence": f"{confidence:.4f}"
        })

    return results


def main():
    """主函数"""
    print("生成训练数据...")
    df = generate_training_data(num_samples=2000)

    # 保存数据供参考
    data_path = os.path.join(os.path.dirname(MODEL_DIR), 'train_data.csv')
    df.to_csv(data_path, index=False)
    print(f"训练数据已保存到: {data_path}")

    # 打印数据分布
    intent_counts = df['intent'].value_counts()
    print(f"数据分布:\n{intent_counts}")

    # 训练模型
    print("开始训练模型...")
    model, tokenizer = train_intent_classifier(df)

    # 测试模型
    test_samples = [
        "推荐一款拍照好的手机",  # recommend
        "华为手机的续航怎么样",  # ask_info
        "苹果手机和小米手机哪个性价比高",  # compare
        "怎么修改我的配送地址"  # unknown
    ]

    results = test_model(model, tokenizer, test_samples)
    print("\n模型测试结果:")
    for result in results:
        print(f"文本: {result['text']}")
        print(f"预测意图: {result['predicted_intent']}")
        print(f"置信度: {result['confidence']}\n")


if __name__ == "__main__":
    main()