import json
from groq import Groq
import os
from dotenv import load_dotenv

class Advisor:
    """Accepts the Metric Contexts provided via the TradingAgent Class and returns a JSON object with some additional evaluations,
    according to its general prompt, detailed in the "prompt" variable.
    """
    def __init__(self, model_name="llama-3.3-70b-versatile"):

        load_dotenv()
        GROQ_KEY_PATH = os.getenv("GROQ_KEY_PATH")

        self.model_name = model_name
        self.client = Groq(
            api_key=GROQ_KEY_PATH
        )

    def analyze(self, context):
        prompt = f"""
        You are a crypto trading assistant.
        Return only valid JSON with these keys:
        bias: one of bullish, neutral, bearish
        confidence: number from 0 to 1
        risk_adjustment: number from 0 to 1
        rationale: short string

        Context:
        {json.dumps(context, indent=2)}

        In the strategy context, there are three strategies: Long Term, focused on DCA and long term alternatives. Swing Trade, focused on
        oportunistic trade opportunities. And hybrid, a mix of these two.
        """

        completion = self.client.chat.completions.create(
            model= self.model_name,
            messages=[
            {
                "role": "system",
                "content": prompt,
            }
            ],
            temperature=1,
            max_completion_tokens=1024,
            top_p=1,
            stream=False,
            response_format={"type": "json_object"},
            stop=None
        )

        return completion.choices[0].message