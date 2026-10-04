import os
import smtplib
import asyncio
from app.core.config import settings

def test_smtp():
    print(f"Testing SMTP with user={settings.SMTP_USER}, host={settings.SMTP_HOST}:{settings.SMTP_PORT}")
    try:
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        code, msg = server.ehlo()
        print(f"EHLO: {code}, {msg}")
        code, msg = server.starttls()
        print(f"STARTTLS: {code}, {msg}")
        code, msg = server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        print(f"LOGIN: {code}, {msg}")
        
        # Test sending with SMTP_USER as from_addr
        from_email = settings.SMTP_USER
        to_email = settings.SMTP_USER
        test_msg = f"Subject: ODIPKS Test\nFrom: {from_email}\nTo: {to_email}\n\nHello from ODIPKS Construction OS!"
        server.sendmail(from_email, [to_email], test_msg)
        print("SENDMAIL: SUCCESS!")
        server.quit()
    except Exception as e:
        print(f"SMTP ERROR: {type(e).__name__}: {e}")

async def test_ai():
    print(f"Testing AI with provider={settings.AI_PROVIDER}")
    from app.services.ai_service import AIVerificationService, AIProvider
    svc = AIVerificationService()
    
    # Test Groq first
    print("\n--- Testing Groq ---")
    svc.provider = AIProvider.GROQ
    try:
        res = await svc.verify_daily_brief({"piling": {"drilled_meters": 18.5}, "alerts": []})
        print(f"GROQ SUCCESS! Risk: {res.risk_assessment}, Summary: {res.executive_summary[:100]}...")
    except Exception as e:
        print(f"GROQ ERROR: {e}")

    # Test Gemini
    print("\n--- Testing Gemini ---")
    svc.provider = AIProvider.GEMINI
    try:
        res = await svc.verify_daily_brief({"piling": {"drilled_meters": 18.5}, "alerts": []})
        print(f"GEMINI Result: Risk: {res.risk_assessment}, Summary: {res.executive_summary[:100]}...")
    except Exception as e:
        print(f"GEMINI ERROR: {e}")

if __name__ == "__main__":
    test_smtp()
    asyncio.run(test_ai())
