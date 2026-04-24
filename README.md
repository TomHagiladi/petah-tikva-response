# מרחב עיבוד משותף · לזכרו של ימנו בנימין זלקה ז״ל

אפליקציית Web חד-פעמית לסדנת מנהלי בתי ספר בפתח תקווה, 26.4.2026. מרחב עיבוד משותף בעקבות רצח ימנו בנימין זלקה ז״ל בליל יום העצמאות. מתוך ההקשר הזה, החלק השני של הסדנה עוסק בבינה מלאכותית כמתווכת של תהליכים קבוצתיים.

**Live:** https://tomhagiladi.github.io/petah-tikva-response/

## מבנה

קובץ SPA יחיד ([`index.html`](index.html)) עם 11 מסכים. אין build step.
- **משתתפ/ת**: welcome → waiting → group → memorial → memory → mood → 💛 heart → 🧠 head → ✊ hands → actions → feedback
- **מנחה**: `?dashboard=true&key=petah-zikaron-2026` (control) או `...&view=display` (מקרן)

## הפעלה

```bash
# מקומית
start index.html

# להחליף את Firebase config לפני פריסה — יש פלייסהולדר REPLACE_ME ב-index.html
# ליצור Firebase project 'petah-tikva-response-2026' ב-console.firebase.google.com (Spark, europe-west1, RTDB test mode)

# בזמן הסדנה: להריץ את סקריפט הסיכום בטרמינל (GEMINI_API_KEY נדרש ב-env)
python summarize.py
```

## תלויות

- Firebase SDK 10.7.1 (Realtime DB)
- Google Fonts: Heebo + Frank Ruhl Libre
- Font Awesome 6
- `google-genai` + `requests` ל-Python (ראה [requirements.txt](requirements.txt))

## רגישויות

- **איסור פרסום** על הנערים החשודים (קטינים). האפליקציה לא מזכירה אותם.
- **כבוד המשפחה** — רק ציטוטים פומביים שכבר פורסמו ברשת.
- **דו-לשוניות מגדרית** בכל טקסט.
- אחרי 26.4.2026 האפליקציה תושבת; אפשר למחוק את פרויקט Firebase לארכוב.

לפרטים על הארכיטקטורה, לראות [CLAUDE.md](CLAUDE.md).
