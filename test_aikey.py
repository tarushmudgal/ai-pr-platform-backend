from openai import OpenAI, APIError, RateLimitError, AuthenticationError
import traceback

# ---------------------------------------
# 🔑 Paste your API key here
API_KEY = "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"
# ---------------------------------------



def log_header(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

def main():
    log_header("OPENAI API KEY DEBUG TEST")

    if not API_KEY.strip():
        print("❌ ERROR: API key field is empty.")
        return

    try:
        log_header("Initializing Client")
        client = OpenAI(api_key=API_KEY)
        print("✔ Client created")

        log_header("Sending Test Request")
        print("→ Model: gpt-4o-mini")
        print("→ Message: 'Hello'")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello!"}],
            max_tokens=5,
        )

        log_header("SUCCESS!")
        print("✔ API key is VALID")
        print("✔ Response:", response.choices[0].message.content)

    
    except AuthenticationError as e:
        log_header("❌ AUTHENTICATION ERROR (Invalid API Key)")
        print("Message:", e)
        print("Type:", type(e).__name__)
        print("\nFull Traceback:")
        traceback.print_exc()

    except RateLimitError as e:
        log_header("❌ RATE LIMIT / QUOTA ERROR")
        print("Message:", e)
        print("Error type:", getattr(e, "code", "unknown"))
        print("Details:", getattr(e, "response", None))
        
        # Detailed classification:
        if "insufficient_quota" in str(e):
            print("\n🔍 DIAGNOSIS: API key is valid but your project HAS NO QUOTA remaining.")
        else:
            print("\n🔍 DIAGNOSIS: You hit a normal rate limit (RPM/TPM).")
        
        print("\nFull Traceback:")
        traceback.print_exc()

    except APIError as e:
        log_header("❌ API ERROR")
        print("Message:", e)
        print("HTTP Status:", getattr(e, "status_code", "unknown"))
        print("Error Code:", getattr(e, "code", "unknown"))
        print("\nFull Traceback:")
        traceback.print_exc()

    except Exception as e:
        log_header("❌ UNEXPECTED ERROR")
        print("Message:", e)
        print("\nFull Traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    main()