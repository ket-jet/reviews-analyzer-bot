import torch
from transformers import GPT2Tokenizer, T5ForConditionalGeneration
import re
import gc
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

# Глобальные переменные для хранения модели и токенизатора
_model = None
_tokenizer = None
_device = None

class Summarizer:
    def __init__(self):
        global _model, _tokenizer, _device

        self.model_name = "RussianNLP/FRED-T5-Summarizer"

        # Ленивая инициализация
        if _model is None or _tokenizer is None:
            logger.info("Ленивая инициализация модели FRED-T5")
            _tokenizer = GPT2Tokenizer.from_pretrained(self.model_name, eos_token='</s>')
            _model = T5ForConditionalGeneration.from_pretrained(self.model_name)
            _device = "cuda" if torch.cuda.is_available() else "cpu"
            _model.to(_device)
            _model.eval()
    
    async def summarize(self, text, field="Комментарий"):
        """
        Суммаризация текста
        
        Args:
            text (str): Текст для суммаризации
            field (str): Тип поля (Достоинства, Недостатки, Комментарий)
            
        Returns:
            str: Суммаризированный текст
        """
        try:
            # Формируем промпт в зависимости от типа поля
            prompts = {
                "Достоинства": "Кратко выдели 3-4 главных достоинства:\n",
                "Недостатки": "Кратко выдели 2-3 главных недостатка:\n",
                "Комментарий": "Обобщи мнение в одном предложении:\n"
            }
            prompt_intro = prompts.get(field, "Обобщи текст:\n")
            input_text = f"<LM> {prompt_intro}{text.strip()}"

            # Токенизируем текст с ограничением длины
            input_ids = _tokenizer.encode(input_text, truncation=True, max_length=512, return_tensors="pt").to(_device)

            # Генерируем суммаризацию
            output = _model.generate(
                input_ids,
                eos_token_id=_tokenizer.eos_token_id,
                num_beams=4,
                min_new_tokens=10,
                max_new_tokens=45 if field != "Комментарий" else 100,
                no_repeat_ngram_size=4,
                do_sample=False,
                early_stopping=True
            )

            # Декодируем результат
            raw_summary = _tokenizer.decode(output[0], skip_special_tokens=True)
            summary_clean = re.sub(r'\d+\.\s*', '', raw_summary).strip()
            summary_clean = re.sub(r'\s+', ' ', summary_clean)

            # Обрезаем до нужного количества предложений
            if field in ["Достоинства", "Недостатки"]:
                sentences = re.findall(r'[^.!?]*[.!?]', summary_clean)
                sentences = [s.strip() for s in sentences if s.strip()]
                max_sentences = 4 if field == "Достоинства" else 3
                summary_clean = ' '.join(sentences[:max_sentences]).strip()

                if not re.search(r'[.!?]$', summary_clean):
                    summary_clean = re.sub(r'[^.!?]*$', '', summary_clean).strip()

            return summary_clean
            
        except Exception as e:
            logger.error(f"Ошибка при суммаризации: {e}")
            return "Не удалось сформировать описание."

    @classmethod
    async def release_model(cls):
        """Ручное освобождение памяти"""
        global _model, _tokenizer, _device
        if _model is not None:
            del _model
            _model = None
            _tokenizer = None
            _device = None
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
            gc.collect()
            logger.info("Модель FRED-T5 успешно удалена из памяти")