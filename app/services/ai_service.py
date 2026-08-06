import os

def get_ai_response(message: str) -> str:
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        return "GROQ_API_KEY not found in environment. Please set GROQ_API_KEY on Render."

    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Effutu Library AI Assistant. Help with book recommendations, "
                        "WASSCE materials, overdue, library info. Be friendly, Ghanaian context.\n"
                        "- Ghana Card format GHA-XXXXXXXXX-X\n"
                        "- Auto-approval via Ghana Card, default password Effutu@XXXX, must change first login\n"
                        "- Present physical Ghana Card on first visit for verification\n"
                        "- Librarian can add/deactivate users at /librarian/users"
                    )
                },
                {"role": "user", "content": message}
            ]
        )
        return response.choices[0].message.content
    except ImportError:
        return "Groq package not installed. Please run `pip install groq`."
    except Exception as e:
        print(f"Groq AI error: {e}")
        return f"AI Assistant temporarily offline. Please contact librarian. Error: {str(e)[:150]}"
