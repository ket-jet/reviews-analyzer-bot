import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class SentimentAnalyzer:
    def __init__(self):
        self.model_name = "cointegrated/rubert-tiny-sentiment-balanced"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        self.model.eval()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        
    async def analyze(self, text):
        """
        Анализ тональности текста
        
        Args:
            text (str): Текст для анализа
            
        Returns:
            tuple: (тональность, уверенность в процентах)
        """
        try:
            # Обрезаем текст до 512 токенов, чтобы избежать ошибки
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                
            # Получаем вероятности для каждого класса
            probs = torch.softmax(outputs.logits, dim=-1).cpu().numpy()[0]
            
            # Определяем тональность и уверенность
            labels = ["негативная", "нейтральная", "положительная"]
            
            # Добавляем дополнительные категории для крайних значений
            if probs[2] > 0.97:  # Очень высокий шанс позитива
                sentiment = "крайне положительная"
            elif probs[0] > 0.97:  # Очень высокий шанс негатива
                sentiment = "крайне отрицательная"
            else:
                sentiment = labels[probs.argmax()]
            
            # Вычисляем уверенность в процентах
            confidence = int(probs.max() * 100)
            
            return sentiment, confidence
        except Exception as e:
            print(f"Ошибка при анализе тональности: {e}")
            return "нейтральная", 0
