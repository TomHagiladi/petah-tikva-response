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
/participants/{userId}      = { name, gender: 'male'|'female', joinedAt, group, currentScreen, readyAt? }
/groups/{groupId}           = { members[], size, createdAt, currentScreen, timer }
/groups/{id}/timer          = { round: 'heart'|'head'|'hands', personalMs, state, speakerIndex, speakerCount, personalEndsAt, groupEndsAt, ... }
/mood/{uid}                 = { text, group, submittedAt }
/moodRequest                = { requestedAt, requestedBy }
/moodSummary                = { status: 'pending'|'generating'|'ready'|'error', text, generatedAt, count }
/actions/{uid}              = { text, group, role: 'individual', name, submittedAt }
/actionsRequest             = { requestedAt, requestedBy }
/actionsSummary             = { status, text, generatedAt, count }
/feedback/{uid}             = { text, name, group, submittedAt }
/summaryRequest             = { requestedAt, requestedBy }
/summary                    = { status, text, generatedAt, count }
```

(Note: `/groups/{id}/summarizer` and the `role: 'group-summary'` variant existed in an earlier
revision when each group could nominate a single member to write on everyone's behalf. The
volunteer-summarizer flow was removed — every participant now writes their own action.)

### Group-level screen sync
"מצאנו ואנחנו מוכנים", "ממשיכים", "קראנו", "סיימנו ממשיכים" — לחיצה של חבר/ת קבוצה אחד/ת מקדמת את כל הקבוצה.
- הכפתור כותב ל-`/groups/{id}/currentScreen` את המסך הבא
- כל לקוח בקבוצה מאזין ומקפיץ `goToScreen(target)` — עם הגנה שהולכת רק קדימה לפי `SCREEN_ORDER`
- **מסכים אישיים** (mood, actions, feedback) — לא מסונכרנים; כל משתתפ/ת ממשיכ/ה בקצב שלו/ה

### Synchronized Group Timer — שלושת הסבבים (Heart/Head/Hands)

הטיימר מאוחד ב-`/groups/{id}/timer` אבל מכיל שדה `round` שמזהה איזה סבב. ב-`ROUND_CONFIG` שבקוד יש מפה של (round name) → (personalMs, next screen, DOM element IDs). בכניסה לכל מסך סבב, הלקוח קורא ל-`setCurrentRound(name)` ו-`listenToGroupTimer()`. ביציאה — `stopListeningToGroupTimer()`. כשהמסך הבא נכנס, `resetTimerForRound(nextRound)` מאפס את מצב הטיימר לסבב החדש.

**Race safety:** כל שינוי טיימר (start/next-speaker/auto-pause) מתבצע ב-`groupTimerRef.transaction()` — רק לקוח אחד "מנצח" גם אם שניים לוחצים במקביל.

**Personal durations:** Heart = 90s, Head = 120s, Hands = 90s.

### Actions Screen — Individual-Only

כל משתתפ/ת כותב/ת לעצמו/ה את הפעולה הפרקטית שיוצא/ת לעשות. אין יותר אופציה של "אני מתנדב/ת לסכם בעבור כולנו" (היא הוסרה אחרי שתום החליט שעדיף שכל אחד/ת יכתבו לבד). אחרי שליחה — נוצר דינמית כפתור "המשיכו" שמעביר אישית למסך המשוב. הכותרת `אפשרות א/ב` והבלוק של state-wait/state-volunteer/state-done הוסרו לחלוטין מה-DOM.

### Gender-Aware UI (.gm / .gf)

לאחר שהמשתמש/ת בוחר/ת זכר/נקבה במסך הרישום, ה-body מקבל class `gender-male` או `gender-female`. CSS מסתיר את הצורה הלא-נכונה של כל טקסט שמסומן ב-`<span class="gm">צורת זכר</span><span class="gf">צורת נקבה</span>`. עד שהמגדר נבחר — שתי הצורות מוסתרות (כדי שלא תופיע כפילות לפני הרישום).

הסיווג נשמר ב-localStorage (`pp-gender`) וב-Firebase (`participants/{uid}/gender`). על boot, `loadIdentity()` קורא ל-`applyGenderClass(gender)` לשחזור.

**איפה השתמשתי במנגנון:** ברוכים הבאים, ממתינים, מסך המזג הרגשי (כולל הדוגמאות), מסך הפעולות, מסך המשוב. שאר המקומות (כותרות הסבבים, הוראות לקבוצה, ציטוטים) נשארים בצורה הדו-לשונית "מנהלים/ות" / "דובר/ת" כי הם מתייחסים לכלל הקבוצה ולא לפנייה אישית.

### למה אין base64 ב-RTDB כאן
האתר הקיים (pitah-tikva-principals) העלה תמונות כ-base64 ב-RTDB. **האתר הזה לא משתמש בתמונות משתתפים** — ה-actions נשלפים כטקסט בלבד. יחסית נקי, לא נדרש Blaze plan. 40 משתתפים × ~500 תווי טקסט = זעיר.

### Assets
- [`assets/yemenu.jpg`](assets/yemenu.jpg) — תמונת פניו של ימנו (שתום סיפק; resize 472×500)
- [`assets/candle.png`](assets/candle.png) — נר זיכרון שיוצר ב-Imagen 4 (Gemini) לפני הבנייה

## תלויות חיצוניות

- **Firebase project** — `petah-tikva-response-2026` נוצר ב-25.4.2026 (Spark plan, europe-west1, RTDB test mode 30 יום). config מלא מוטמע ב-`index.html`. ה-rules פתוחות לקריאה/כתיבה ללא auth — מתאים לסדנה חד-פעמית.
- **ADMIN_KEY** קבוע ב-`index.html` = `'petah-zikaron-2026'`. שינוי דורש עדכון הלינק שתום שומר.
- **Gemini API** — שלושת הסיכומים (mood, actions, feedback) דורשים `summarize.py` לרוץ על הלפטופ של תום בזמן הסדנה. `GEMINI_API_KEY` חייב להיות ב-env. המפתח **לא** מוטמע ב-index.html.
  - הגבלת IP הוסרה זמנית (כמו בפרויקט הקיים) — ה-ISP של תום מחלף IP דינמית.

## Gotchas שנשמרו / חדשים

- **גודל קבוצה 5 בלתי אפשרי** — אלגוריתם `computeGroupsPreview()` תומך רק ב-3/4. הדשבורד מציג אזהרה עבור 1, 2, 5.
- **Chrome ב-Windows ו-`start`** — query strings (`?dashboard=true&key=...` ו-`?fresh=1`) מתבלבלים. Windows מפרש את ה-`?` כחלק משם הקובץ ולא כפרמטר. חייב לפתוח דרך chrome.exe ישירות:
  ```bash
  "C:/Program Files/Google/Chrome/Application/chrome.exe" --new-window "file:///.../index.html?fresh=1"
  ```
- **שפה**: דו-לשוניות מגדרית עבור כל טקסט שמתייחס לכלל הקבוצה ("מנהלים/ות", "דובר/ת"). פניות אישיות ישירות (welcome, mood prompt, actions prompt, feedback prompt) מותאמות מגדרית דרך `.gm`/`.gf` spans + body class — ראה "Gender-Aware UI" למעלה.
- **איסור פרסום**: החשודים ברצח הם קטינים; האפליקציה **לא** מזכירה אותם. הטקסט של מסך 5 בנוי בכוונה על ציטוטי אנשים שאהבו את ימנו.
- **שמירה על כבוד המשפחה**: לא לדבר בשמם; רק הציטוט "מרוסקים ושבורי לב" ו"ילד טהור ותמים".
- **Gemini thinking=0**: כבוי (כמו בפרויקט הקיים — אחרת עברית נחתכת באמצע משפט).
- **summarize.py — UTF-8 stdout חובה** (Windows-specific gotcha חמור): טרמינל cp1252 לא יודע לקודד תווים כמו ✅. בעבר זה גרם לסקריפט להיתקע בלולאה אינסופית — `print(✅)` היה זורק אחרי שהסיכום נוצר אבל לפני ש-`last_seen` עודכן, אז אותה בקשה עובדה שוב ושוב לנצח. הפתרון:
  1. הסקריפט מבצע `sys.stdout.reconfigure(encoding="utf-8")` בעלייה.
  2. כל ה-prints עטופים ב-`safe_print()` שלעולם לא זורק.
  3. `last_seen` מתעדכן **מיד** כשמזהים בקשה חדשה — לפני כל עבודה כבדה.

  אם תוסיף/י pipeline נוסף, חשוב לשמור על העקרון: סמן כ-seen מיד, עטוף הכל ב-try/except, השתמש/י ב-`safe_print` לא ב-`print`.
- **summarize.py polling** — צריך לרוץ *לפני* שתום לוחץ על אחד מכפתורי הסיכום. אם לא רץ והוא לחץ — הסטטוס נתקע ב-`pending`. כשמתחילים את הסקריפט הוא מסמן את ה-requestedAt הקיים כ"כבר ראיתי" כדי לא לעבד בקשות ישנות. הפתרון אם זה קרה: למחוק `/{kind}Request` וללחוץ שוב מהדשבורד.
- **מצב Fresh (debug)** — `?fresh=1` מחליף `localStorage` ב-`sessionStorage`. קריטי לבדיקות רב-משתמש במחשב אחד; כל חלון Chrome חדש (`--new-window`) שנפתח עם `?fresh=1` נחשב משתמש שונה.
- **Display view = anonymous** — כשמסך התצוגה (למקרן) מציג את קיר הפעולות, שמות ומספרי קבוצות מוסתרים אוטומטית דרך CSS rule `body.dashboard-display .action-meta { display: none }`. אם תוסיף/י metadata חדש — תן לו class `action-meta` כדי שיוסתר באותה תצוגה.

## דברים שלא נמצאים בפרויקט אבל היו בסדנה הקודמת (pitah-tikva-principals)

- **base64 photo upload + collage wall** — הוסר כי האירוע לא מתאים לעידוד צילום סלפי.
- **battery slider + 3 character images** — הוחלף בכתיבה אנונימית של "המזג הרגשי" (טקסט חופשי שעובר ל-Gemini).
- **שיר "לובשת שגרה"** — לא רלוונטי כאן; הוחלף במסך זיכרון של ימנו.
- **`done` screen** — אין מסך סיום נפרד. מסך המשוב הוא האחרון; אחרי שליחה הוא מתחלף להודעת תודה.
