"""
summarize.py — runs on the facilitator's laptop during the workshop.

מאזין לשלוש בקשות סיכום ב-Firebase RTDB:
  /moodRequest      → מסכם את /mood/*        → /moodSummary       (המזג הרגשי בחדר)
  /actionsRequest   → מסכם את /actions/*     → /actionsSummary    (רשימת פעולות פרקטיות)
  /summaryRequest   → מסכם את /feedback/*    → /summary           (משוב על החוויה הטכנולוגית)

בכל פעם שתום לוחץ על אחד מכפתורי הסיכום בדשבורד הבקרה, בקשה חדשה נכתבת ל-DB.
הסקריפט מזהה איזו בקשה התחדשה, שולף את הנתונים, שולח ל-Gemini, וכותב את התוצאה חזרה.

הפעלה:
    # ודא/י ש-GEMINI_API_KEY מוגדר ב-env (מוגדר אצל תום כ-Windows env var).
    python summarize.py

השאר/י את הסקריפט רץ בטרמינל לאורך הסדנה. Ctrl+C לעצירה.
"""
import os
import sys
import time
import requests
from google import genai
from google.genai import types

# Force UTF-8 stdout so Hebrew + emoji work on Windows cp1252 terminals.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DB_URL = "https://petah-tikva-response-2026-default-rtdb.europe-west1.firebasedatabase.app"
MODEL = "gemini-2.5-flash"
POLL_SECONDS = 3


# ===========================================================================
#  פרומפטים — אחד לכל סוג סיכום
# ===========================================================================

MOOD_PROMPT = """את/ה מקבל/ת רשימה של משפטים קצרים אנונימיים שנכתבו על ידי מנהלי ומנהלות בתי ספר בפתח תקווה, בפתיחת סדנה משותפת לעיבוד רצח הצעיר ימנו בנימין זלקה ז״ל בעירם.

המטרה: לזקק פסקה אחת שמשקפת בדייקנות את המקום הרגשי בחדר. התובנה תוקרן במליאה בתחילת הדיון.

כללים:
1. עיגון בציטוטים קצרים מדויקים. אם מישהי כתבה "אני כועסת" — צטט/י; אם מישהו כתב "משהו בי כבה" — הבא/י בדיוק את הניסוח.
2. שקף/י גיוון אמיתי. אם יש עוצמה של כעס לצד הלם שקט, או מי שמרגיש/ה חוסר אונים לצד מי שמרגיש/ה אחריות — הזכר/י את זה בתפיסה. אל תשטח/י הכל ל"חוויה מגוונת".
3. אורך: 4-5 משפטים רציפים, פסקה אחת. ללא כותרות, ללא bullets.
4. טון: ניטרלי, מכובד, מדויק. אמפתי ולא פתטי. נוכח ולא פולמוסי.
5. אסור: שמות, הכללות בסגנון "עולה מהמשובים", פתיחות בסגנון "המשפטים משקפים".
6. התחל/י ישירות מהתוכן הקונקרטי — מה באמת בחדר.

המשפטים שנכתבו:
{items}"""


ACTIONS_PROMPT = """את/ה מקבל/ת רשימה של פעולות שמנהלי ומנהלות בתי ספר בפתח תקווה כתבו בעקבות רצח הצעיר ימנו בנימין זלקה ז״ל. כל אחד/ת תיאר/ה מה הוא/היא הולך/ת לעשות בבית הספר שלו/ה.

המטרה: לזקק רשימה של פעולות פרקטיות, קונקרטיות ובנות-ביצוע, שתשמש לקולגות שמתלבטים/ות איך להגיב. הרשימה תוקרן במליאה.

כללים:
1. חלק/י את הרשימה לארבע קטגוריות:
   א. פעולות מיידיות עם הצוות
   ב. פעולות מיידיות עם התלמידים/ות
   ג. פעולות עם ההורים והקהילה
   ד. החלטות מערכתיות בית-ספריות
2. בכל קטגוריה — רשימה של פעולות (כל אחת משפט אחד ברור וישים). כמה שיש. אין מגבלה על הכמות.
3. אחד את פעולות דומות שחזרו ממספר מנהלים/ות לפריט אחד מאוחד — אבל שמור/י את ה"בשר" (למשל: "שיח צוות מחנכים/ות בתחילת השבוע על מה האירוע חושף").
4. כתב/י רק פעולות שבאמת הופיעו בטקסטים — אל תמציא/י.
5. אם קטגוריה ריקה — כתוב/י "—".
6. פורמט: כותרת קטגוריה בהדגשה, מתחתיה רשימה עם "• " בתחילת כל שורה.
7. ללא פתיחות, ללא סיכום חותם. ישר לרשימה.

הטקסטים שנשלחו (ייתכנו פריטים של יחיד/ה ופריטים של סיכום קבוצתי):
{items}"""


FEEDBACK_PROMPT = """את/ה מקבל/ת משובים של מנהלי ומנהלות בתי ספר בפתח תקווה על החוויה של שימוש באפליקציה (מופעלת ע"י בינה מלאכותית) כדי לעבד בקבוצות קטנות את רצח ימנו בנימין זלקה ז״ל. המשוב הוא על *חוויית השימוש בטכנולוגיה* — לא על תוכן העיבוד עצמו.

המטרה: לזקק פסקה מדויקת שתוצג במליאה ותשמש כגשר לחלק השני של המפגש (הדרכה על בניית מערכות כאלה). הדגש את מה שעבד, את מה שהפריע, את השאלות שעלו על האיזון בין אנושי לטכנולוגי, ואת הפתעות אמיתיות.

כללים:
1. עיגון בציטוטים מדויקים וקצרים מתוך המשובים.
2. זיהוי 2-3 מוטיבים חוזרים — נסח/י כל אחד במשפט שמחזיק רמז לתוכן, לא רק שם הנושא.
3. אורך: 4-6 משפטים. פסקה רציפה.
4. טון: מדויק, ביקורתי-כנה, לא שיווקי. אפשר להביא גם סתירות (מישהו אהב, מישהי לא).
5. אסור: שמות, הכללות ריקות, משפטי פתיחה כמו "המשובים משקפים".
6. התחל/י ישירות בתוכן הקונקרטי שעלה.

המשובים:
{items}"""


# ===========================================================================
#  תצורה לכל pipeline
# ===========================================================================

PIPELINES = {
    "mood": {
        "request_path": "moodRequest",
        "source_path": "mood",
        "target_path": "moodSummary",
        "label": "מזג רגשי",
        "prompt_template": MOOD_PROMPT,
        "temperature": 0.7,
    },
    "actions": {
        "request_path": "actionsRequest",
        "source_path": "actions",
        "target_path": "actionsSummary",
        "label": "פעולות פרקטיות",
        "prompt_template": ACTIONS_PROMPT,
        "temperature": 0.4,  # More deterministic — we're clustering, not interpreting
    },
    "feedback": {
        "request_path": "summaryRequest",
        "source_path": "feedback",
        "target_path": "summary",
        "label": "משוב על החוויה",
        "prompt_template": FEEDBACK_PROMPT,
        "temperature": 0.8,
    },
}


# ===========================================================================
#  HTTP
# ===========================================================================

def fetch(path):
    r = requests.get(f"{DB_URL}/{path}.json", timeout=10)
    r.raise_for_status()
    return r.json()


def put(path, data):
    r = requests.put(f"{DB_URL}/{path}.json", json=data, timeout=10)
    r.raise_for_status()
    return r.json()


# ===========================================================================
#  Gemini
# ===========================================================================

def build_items_text(items_dict):
    """Convert a dict of {uid: {text, ...}} into a bullet list of non-empty texts."""
    lines = []
    for _uid, item in (items_dict or {}).items():
        text = ((item or {}).get("text") or "").strip()
        if text:
            lines.append(f"- {text}")
    return "\n".join(lines)


def generate_summary(pipeline_name, items_text):
    cfg = PIPELINES[pipeline_name]
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = cfg["prompt_template"].format(items=items_text)
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            # Disable thinking — it eats the output budget and truncates Hebrew mid-sentence.
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            max_output_tokens=4096 if pipeline_name == "actions" else 2048,
            temperature=cfg["temperature"],
        ),
    )
    return (response.text or "").strip()


# ===========================================================================
#  Main loop
# ===========================================================================

def safe_print(*args, **kwargs):
    """Print that never raises — Windows terminals sometimes can't encode chars."""
    kwargs.setdefault("flush", True)
    try:
        print(*args, **kwargs)
    except Exception:
        try:
            msg = " ".join(str(a) for a in args).encode("ascii", "replace").decode("ascii")
            print(msg, **kwargs)
        except Exception:
            pass


def process_pipeline(pipeline_name, last_seen):
    """Check a single pipeline for a new request. Returns updated last_seen.

    CRITICAL: Once we observe a new requested_at, we mark it as seen immediately
    and never re-process it — even if the rest of the processing fails. Otherwise
    a single failure (e.g. encoding error in a print) creates an infinite loop.
    """
    cfg = PIPELINES[pipeline_name]
    try:
        req = fetch(cfg["request_path"])
    except Exception as e:
        safe_print(f"  [{cfg['label']}] שגיאה בקריאת בקשה: {e}")
        return last_seen

    if not (req and isinstance(req, dict)):
        return last_seen

    requested_at = req.get("requestedAt")
    if not requested_at or requested_at == last_seen:
        return last_seen

    # MARK AS SEEN IMMEDIATELY — never re-process the same request.
    new_last_seen = requested_at

    try:
        safe_print(f"\n[{cfg['label']}] בקשה חדשה (ts={requested_at})")

        try:
            items = fetch(cfg["source_path"]) or {}
        except Exception as e:
            safe_print(f"  [{cfg['label']}] שגיאה בשליפת נתונים: {e}")
            try:
                put(cfg["target_path"], {"status": "error", "error": str(e)[:200]})
            except Exception:
                pass
            return new_last_seen

        if not items:
            safe_print(f"  [{cfg['label']}] אין עדיין טקסטים לסיכום")
            try:
                put(cfg["target_path"], {"status": "error", "error": "אין עדיין טקסטים"})
            except Exception:
                pass
            return new_last_seen

        text = build_items_text(items)
        count = len([v for v in items.values() if (v or {}).get("text")])
        safe_print(f"  [{cfg['label']}] נמצאו {count} טקסטים, שולח ל-Gemini...")

        try:
            put(cfg["target_path"], {"status": "generating"})
        except Exception:
            pass

        try:
            summary = generate_summary(pipeline_name, text)
        except Exception as e:
            safe_print(f"  [{cfg['label']}] שגיאת Gemini: {e}")
            try:
                put(cfg["target_path"], {"status": "error", "error": str(e)[:200]})
            except Exception:
                pass
            return new_last_seen

        try:
            put(
                cfg["target_path"],
                {
                    "status": "ready",
                    "text": summary,
                    "generatedAt": int(time.time() * 1000),
                    "count": count,
                },
            )
        except Exception as e:
            safe_print(f"  [{cfg['label']}] שגיאה בכתיבת הסיכום: {e}")
            return new_last_seen

        safe_print(f"  [{cfg['label']}] OK נכתב ({len(summary)} תווים)")
        safe_print(f"--- {cfg['label']} ---\n{summary}\n---")
    except Exception as e:
        safe_print(f"  [{cfg['label']}] שגיאה לא צפויה: {e}")

    return new_last_seen


def main():
    if not os.environ.get("GEMINI_API_KEY"):
        print("חסר GEMINI_API_KEY במשתני הסביבה. הגדר אותו ונסה שוב.", flush=True)
        sys.exit(1)

    print(f"מחובר ל-{DB_URL}", flush=True)
    print(f"מודל: {MODEL}", flush=True)
    print(f"בודק כל {POLL_SECONDS} שניות. Ctrl+C לעצירה.\n", flush=True)

    # Snapshot current state so we don't re-process old requests on startup
    last_seen = {}
    for name, cfg in PIPELINES.items():
        last_seen[name] = None
        try:
            current = fetch(cfg["request_path"])
            if current and isinstance(current, dict):
                ts = current.get("requestedAt")
                if ts:
                    last_seen[name] = ts
                    print(f"  [{cfg['label']}] בקשה קיימת (ts={ts}) — מתעלם", flush=True)
        except Exception as e:
            print(f"  [{cfg['label']}] אזהרה בקריאה ראשונית: {e}", flush=True)

    while True:
        try:
            for name in PIPELINES:
                last_seen[name] = process_pipeline(name, last_seen[name])
            time.sleep(POLL_SECONDS)
        except KeyboardInterrupt:
            print("\nעצירה.", flush=True)
            break
        except Exception as e:
            print(f"אזהרה: {e} — מנסה שוב בעוד {POLL_SECONDS} שניות", flush=True)
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
