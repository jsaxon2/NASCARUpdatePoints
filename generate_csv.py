import os
import sys
import time
from google import genai
from google.genai import types

def generate_weekly_csv():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    prompt = """
    Provide the NASCAR Cup Series race results for all 36 drivers in the most recent completed race.
    Format as a raw CSV block without markdown fences.
    
    Header format:
    Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap
    """

    # Retry logic for 429 Rate Limits
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Using model without Search Grounding overhead to conserve quota
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1
                )
            )

            if response and response.text:
                csv_text = response.text.strip()
                if csv_text.startswith("```"):
                    csv_text = csv_text.split("\n", 1)[1]
                if csv_text.endswith("```"):
                    csv_text = csv_text.rsplit("\n", 1)[0]
                csv_text = csv_text.replace("```csv", "").strip()

                with open("race_results.csv", "w", encoding="utf-8") as f:
                    f.write(csv_text)
                    
                print("race_results.csv created successfully!")
                return

        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(f"Quota exceeded (429). Retrying in 30 seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(30)
            else:
                print(f"Error generating CSV: {e}")
                sys.exit(1)

    print("Error: Exceeded max retries due to quota rate limits.")
    sys.exit(1)

if __name__ == "__main__":
    generate_weekly_csv()
