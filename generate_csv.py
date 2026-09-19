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
    Format as a raw CSV block without markdown fences or extra commentary.
    
    Header format:
    Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap
    """

    max_retries = 5
    base_delay = 10  # Seconds to wait before first retry

    for attempt in range(1, max_retries + 1):
        try:
            print(f"Sending request to Gemini API (Attempt {attempt}/{max_retries})...")
            
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
            err_msg = str(e)
            if "503" in err_msg or "UNAVAILABLE" in err_msg or "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                wait_time = base_delay * (2 ** (attempt - 1))
                print(f"Temporary server overload/quota error: {e}")
                print(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
            else:
                print(f"Non-retryable error encountered: {e}")
                sys.exit(1)

    print("Error: Max retries exceeded. API remained unavailable.")
    sys.exit(1)

if __name__ == "__main__":
    generate_weekly_csv()
