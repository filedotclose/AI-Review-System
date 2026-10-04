import os
import smtplib
from app.core.config import settings

password = settings.SMTP_PASSWORD
users_to_test = [
    settings.SMTP_USER,           # Axsinfra@gmail.com
    "work.sujalagarwal@gmail.com", # Alternative recipient/user
]

print(f"Testing SMTP authentication with password length={len(password)}...")

for user in users_to_test:
    if not user:
        continue
    print(f"\n==========================================")
    print(f"Testing user: {user}")
    print(f"==========================================")
    
    # 1. Test Port 587 STARTTLS
    print(f"• Attempting Port 587 (STARTTLS)...")
    try:
        s = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
        s.ehlo()
        s.starttls()
        s.ehlo()
        code, msg = s.login(user, password)
        print(f"  ✓ LOGIN SUCCESS on Port 587! Code: {code}")
        
        # Test sending
        test_msg = f"Subject: ODIPKS Live Test from Port 587\nFrom: {user}\nTo: work.sujalagarwal@gmail.com\n\nSMTP on Port 587 is working perfectly!"
        s.sendmail(user, ["work.sujalagarwal@gmail.com"], test_msg)
        print("  ★ EMAIL SENT SUCCESSFULLY ON PORT 587!")
        s.quit()
        break
    except Exception as e:
        print(f"  ✗ Port 587 failed: {type(e).__name__}: {e}")

    # 2. Test Port 465 SSL
    print(f"• Attempting Port 465 (SSL Direct)...")
    try:
        s = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10)
        s.ehlo()
        code, msg = s.login(user, password)
        print(f"  ✓ LOGIN SUCCESS on Port 465! Code: {code}")
        
        # Test sending
        test_msg = f"Subject: ODIPKS Live Test from Port 465\nFrom: {user}\nTo: work.sujalagarwal@gmail.com\n\nSMTP on Port 465 is working perfectly!"
        s.sendmail(user, ["work.sujalagarwal@gmail.com"], test_msg)
        print("  ★ EMAIL SENT SUCCESSFULLY ON PORT 465!")
        s.quit()
        break
    except Exception as e:
        print(f"  ✗ Port 465 failed: {type(e).__name__}: {e}")
