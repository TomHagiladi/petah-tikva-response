# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## מה זה

אפליקציית Web חד-פעמית לסדנת מנהלי בתי ספר בפתח תקווה, **26.4.2026**, ~40 משתתפים (10 קבוצות של 3-4). הסדנה מוקדשת ל**עיבוד משותף של רצח ימנו בנימין זלקה ז״ל** — צעיר בן 21 שנדקר בליל יום העצמאות האחרון בפתח תקווה ונפטר מפצעיו יומיים אחר כך. מתוך ההקשר הזה, החלק השני של הסדנה עוסק בבינה מלאכותית כמתווכת של תהליכים קבוצתיים.

**זהו Fork של הפרויקט [`pitah-tikva-principals`](../pitah-tikva-principals/).** האתר המקורי (Vibe Coding) נשמר ללא שינוי לסדנאות עתידיות. הפרויקט החדש מתבסס על אותה תשתית טכנית (timer מסונכרן, group-screen-sync, Firebase RTDB, summarize.py polling) עם רצף מסכים, פלטה וקונטנט חדשים לחלוטין.

**Live URL:** https://tomhagiladi.github.io/petah-tikva-response/ (GitHub Pages, branch=main, path=/)
**Repo:** https://github.com/TomHagiladi/petah-tikva-response (public)

אחרי 26.4.2026 האפליקציה תושבת; אפשר למחוק את פרויקט Firebase לארכוב.

## Commands

```bash
# הפעלה מקומית
start index.html                                                     # משתתפ/ת רגיל/ה
start "index.html?dashboard=true&key=petah-zikaron-2026"              # דשבורד מנחה — Control view
start "index.html?dashboard=true&key=petah-zikaron-2026&view=display" # דשבורד מנחה — Display view (למקרן)
start "index.html?fresh=1"                                           # משתתפ/ת עם זהות חדשה (לבדיקות רב-משתמש במחשב אחד)
start "index.html?screen=mood"                                       # קפיצה למסך X — welcome/waiting/group/memorial/memory/mood/heart/head/hands/actions/feedback

# פתיחה מדויקת דרך Chrome (ב-Windows, start מתבלבל עם query params)
"C:/Program Files/Google/Chrome/Application/chrome.exe" "file:///C:/Users/tomha/claude%20code/workshops/petah-tikva-response/index.html?dashboard=true&key=petah-zikaron-2026"

# ניקוי Firebase (הדשבורד מספק כפתור "אתחול הסדנה" שעושה את אותו הדבר)
curl -X DELETE "https://petah-tikva-response-2026-default-rtdb.europe-west1.firebasedatabase.app/.json"

# סקריפט סיכום — חייב לרוץ בטרמינל בזמן הסדנה (GEMINI_API_KEY נדרש בסביבה)
python summarize.py

# פריסה: push ל-main של GitHub repo `TomHagiladi/petah-tikva-response` מתעדכן ב-Pages תוך ~1-2 דק'
git push   # → https://tomhagiladi.github.io/petah-tikva-response/
```

אין build step, אין lint, אין tests. SPA קובץ יחיד.

## ארכיטקטורה

**קובץ אחד — [index.html](index.html)** מכיל את כל ה-HTML, CSS ו-JS inline. הספריות היחידות: Firebase SDK 10.7.1 (app + database), Google Fonts (Heebo + Frank Ruhl Libre), Font Awesome 6.

### שלוש תצוגות מאותו קובץ
- **משתתפ/ת** (default) — 11 מסכים: welcome → waiting → group → memorial → memory → mood → heart → head → hands → actions → feedback
- **מנחה Control** (`?dashboard=true&key=petah-zikaron-2026`) — פאנל ניהול: חלוקה לקבוצות, 3 כפתורי סיכום (mood/actions/feedback), קיר הפעולות, סיכומי Gemini
- **מנחה Display** (`?dashboard=true&key=petah-zikaron-2026&view=display`) — נפרס על המקרן. מסתיר את פאנל הניהול; מציג רק את סיכום המזג הרגשי, קיר הפעולות, רשימת הפעולות המזוקקת, וסיכום המשוב על החוויה

הבחירה נעשית ב-boot דרך `isDashboardMode()` + `getDashboardView()`.

### Firebase Realtime Database schema

```
/participants/{userId}      = { name, joinedAt, group, currentScreen, readyAt? }
/groups/{groupId}           = { members[], size, createdAt, currentScreen, timer, summarizer? }
/groups/{id}/timer          = { round: 'heart'|'head'|'hands', personalMs, state, speakerIndex, speakerCount, personalEndsAt, groupEndsAt, ... }
/groups/{id}/summarizer     = { uid, name, status: 'writing'|'done' }
/mood/{uid}                 = { text, group, submittedAt }
/moodRequest                = { requestedAt, requestedBy }
/moodSummary                = { status: 'pending'|'generating'|'ready'|'error', text, generatedAt, count }
/actions/{uid}              = { text, group, role: 'individual'|'group-summary', name, submittedAt }
/actionsRequest             = { requestedAt, requestedBy }
/actionsSummary             = { status, text, generatedAt, count }
/feedback/{uid}             = { text, name, group, submittedAt }
/summaryRequest             = { requestedAt, requestedBy }
/summary                    = { status, text, generatedAt, count }
```

### Group-level screen sync
"מצאנו ואנחנו מוכנים", "ממשיכים", "קראנו", "סיימנו ממשיכים" — לחיצה של חבר/ת קבוצה אחד/ת מקדמת את כל הקבוצה.
- הכפתור כותב ל-`/groups/{id}/currentScreen` את המסך הבא
- כל לקוח בקבוצה מאזין ומקפיץ `goToScreen(target)` — עם הגנה שהולכת רק קדימה לפי `SCREEN_ORDER`
- **מסכים אישיים** (mood, actions, feedback) — לא מסונכרנים; כל משתתפ/ת ממשיכ/ה בקצב שלו/ה

### Synchronized Group Timer — שלושת הסבבים (Heart/Head/Hands)

הטיימר מאוחד ב-`/groups/{id}/timer` אבל מכיל שדה `round` שמזהה איזה סבב. ב-`ROUND_CONFIG` שבקוד יש מפה של (round name) → (personalMs, next screen, DOM element IDs). בכניסה לכל מסך סבב, הלקוח קורא ל-`setCurrentRound(name)` ו-`listenToGroupTimer()`. ביציאה — `stopListeningToGroupTimer()`. כשהמסך הבא נכנס, `resetTimerForRound(nextRound)` מאפס את מצב הטיימר לסבב החדש.

**Race safety:** כל שינוי טיימר (start/next-speaker/auto-pause) מתבצע ב-`groupTimerRef.transaction()` — רק לקוח אחד "מנצח" גם אם שניים לוחצים במקביל.

**Personal durations:** Heart = 90s, Head = 120s, Hands = 90s.

### Actions Screen — Volunteer Summarizer Pattern

מסך הפעולות (screen 10) מגיע עם ארבעה מצבים:
- **own** — ברירת מחדל: המשתתפ/ת יכול/ה לכתוב משלו/ה, או ללחוץ "אני מתנדב/ת לסכם בעבור כולנו"
- **wait** — מישהו/י אחר/ת בקבוצה כבר התנדב/ה; המשתתפ/ת רואה/ת את שמו/ה וממתינ/ה
- **volunteer** — המשתתפ/ת ה*זה*/*זאת* התנדב/ה; מקבל/ת textarea גדול/ה לכתיבה בעבור הקבוצה
- **done** — הסיכום הקבוצתי נשלח; כל חברי/ות הקבוצה רואים/ות כפתור "המשיכו"

**Race safety:** הלחיצה על "אני מתנדב/ת לסכם" מתבצעת ב-transaction על `/groups/{id}/summarizer`. אם מישהו/י אחר/ת הקדים/ה — החוזה לא מחויב והלקוח שלנו עובר ל-wait.

**Skip for individuals:** משתתפ/ת שכתב/ה משלו/ה (role='individual') מקבל/ת כפתור "המשיכו" מיידי אחרי השליחה. משתתפ/ת שהתנדב/ה וסיים/ה (role='group-summary', status='done') — כל חברי/ות הקבוצה רואים/ות את אותו כפתור.

### למה אין base64 ב-RTDB כאן
האתר הקיים (pitah-tikva-principals) העלה תמונות כ-base64 ב-RTDB. **האתר הזה לא משתמש בתמונות משתתפים** — ה-actions נשלפים כטקסט בלבד. יחסית נקי, לא נדרש Blaze plan. 40 משתתפים × ~500 תווי טקסט = זעיר.

### Assets
- [`assets/yemenu.jpg`](assets/yemenu.jpg) — תמונת פניו של ימנו (שתום סיפק; resize 472×500)
- [`assets/candle.png`](assets/candle.png) — נר זיכרון שיוצר ב-Imagen 4 (Gemini) לפני הבנייה

## תלויות חיצוניות

- **Firebase config** מוטמע ב-`index.html`. **הפרויקט עדיין לא נוצר** — יש placeholder `REPLACE_ME` שם. תום יצטרך ליצור את הפרויקט `petah-tikva-response-2026` ב-console.firebase.google.com (Spark plan, region europe-west1, Realtime Database test mode 30 יום), ולהדביק את ה-config.
- **ADMIN_KEY** קבוע ב-`index.html` = `'petah-zikaron-2026'`. שינוי דורש עדכון הלינק שתום שומר.
- **Gemini API** — שלושת הסיכומים (mood, actions, feedback) דורשים `summarize.py` לרוץ על הלפטופ של תום בזמן הסדנה. `GEMINI_API_KEY` חייב להיות ב-env. המפתח **לא** מוטמע ב-index.html.
  - הגבלת IP הוסרה זמנית (כמו בפרויקט הקיים) — ה-ISP של תום מחלף IP דינמית.

## Gotchas שנשמרו / חדשים

- **גודל קבוצה 5 בלתי אפשרי** — אלגוריתם `computeGroupsPreview()` תומך רק ב-3/4. הדשבורד מציג אזהרה עבור 1, 2, 5.
- **Chrome ב-Windows ו-`start`** — query strings (`?dashboard=true&key=...`) מתבלבלים. חייב לפתוח דרך chrome.exe ישירות.
- **שפה**: **דו-לשוניות מגדרית בכל טקסט** — "מנהלים/ות", "דובר/ת", "את/ה", "לכם/ן". אין טקסט שלא פונה לשני המגדרים.
- **איסור פרסום**: החשודים ברצח הם קטינים; האפליקציה **לא** מזכירה אותם. הטקסט של מסך 5 בנוי בכוונה על ציטוטי אנשים שאהבו את ימנו.
- **שמירה על כבוד המשפחה**: לא לדבר בשמם; רק הציטוט "מרוסקים ושבורי לב" ו"ילד טהור ותמים".
- **Gemini thinking=0**: כבוי (כמו בפרויקט הקיים — אחרת hebrew מתחתך באמצע משפט).
- **מצב Fresh (debug)** — `?fresh=1` מחליף `localStorage` ב-`sessionStorage`. קריטי לבדיקות רב-משתמש במחשב אחד.
- **summarize.py** — צריך לרוץ *לפני* שתום לוחץ על אחד מכפתורי הסיכום. אם לא רץ — הסטטוס נתקע ב-`pending`.

## שלב הבא (לבנייה בפועל)

1. ✅ כל הקוד מוכן במקומי.
2. יש ליצור את פרויקט Firebase וה-GitHub repo (הוראות מפורטות ב-README).
3. להדביק את ה-Firebase config ב-index.html.
4. לדחוף ל-GitHub → GitHub Pages.
5. לבדוק multi-user עם `?fresh=1`.
