# Inspirationsarchiv

[简体中文](README.md) · [English](README.en.md) · [Deutsch](README.de.md)

[Erste Version herunterladen](https://github.com/xuan0707-lll/inspiration-inbox/archive/refs/tags/v0.1.0-alpha.1.zip) · [Kurzbefehl fürs iPhone laden](https://github.com/xuan0707-lll/inspiration-inbox/raw/refs/heads/main/mobile/存到灵感库.shortcut) · [Einrichtung](#einrichtung)

Das Inspirationsarchiv macht aus Videos und Bildbeiträgen, die du auf dem Smartphone entdeckst, durchsuchbare Obsidian-Notizen. So kannst du sie später beim Schreiben, bei der Arbeit oder in kreativen Projekten mit KI weiterverwenden.

**Die erste Version ist für einen Mac mit Apple-Chip und ein iPhone gedacht.** Auf beiden Geräten muss Obsidian eingerichtet und die Synchronisierung über iCloud Drive aktiviert sein. Links kannst du jederzeit auf dem iPhone speichern. Die Transkription erfolgt lokal auf dem Mac, ohne kostenpflichtige Transkriptionsminuten oder KI-Guthaben. Ist der Mac ausgeschaltet oder im Ruhezustand, bleiben die Links im Eingang. Sobald der Mac wieder läuft, online ist und der Hintergrunddienst gestartet wurde, werden sie verarbeitet.

Derzeit werden **Douyin, Bilibili und Xiaohongshu (RedNote)** unterstützt. Jede Videonotiz enthält den Originallink und, sofern verfügbar, den Begleittext des Beitrags. Der gesprochene Inhalt wird in Absätze gegliedert und erhält einen passenden Kurztitel. Am Ende steht eine Gliederung zur schnellen Orientierung.

## 1. Videos automatisch transkribieren

Wenn du ein nützliches Video entdeckst, **kopiere den Link und tippe im Kontrollzentrum des iPhones auf „Im Inspirationsarchiv speichern“**. Während du weiterscrollst, übernimmt der Mac die Transkription und Aufbereitung. Erinnerst du dich später nur noch an ein Stichwort, kannst du die entsprechende Passage in Obsidian suchen und direkt zitieren. So wird aus einem Video, das sonst in den Favoriten verstauben würde, brauchbares Material. Das Suchen nach dem Original, erneute Abspielen und Abtippen entfallen.

## 2. Text aus Bildern und erste Beschreibungen von Videoszenen

Bei einem Bildbeitrag auf Xiaohongshu kopierst du ebenfalls den Link und tippst auf „Im Inspirationsarchiv speichern“. Der Mac erkennt den Text jedes Bildes und ordnet ihn in der Notiz in der ursprünglichen Reihenfolge dem jeweiligen Bild zu. Begleittext und Originallink bleiben erhalten. Verteilt sich eine Anleitung über mehrere Bilder, findest du mit einem Stichwort die passende Seite. Auch ein KI-Assistent kann den erkannten Text direkt auswerten.

Interessieren dich die **Bildgestaltung oder eine Animation**, wähle im Teilen-Menü „Im Inspirationsarchiv speichern“ und ergänze einen Hinweis, etwa „Titelanimation in den ersten drei Sekunden ansehen“. Das Werkzeug speichert den Hinweis zusammen mit dem Link und erstellt anhand einzelner Videobilder eine erste Beschreibung. Ein KI-Assistent mit Zugriff auf deine Notizen weiß damit, was dich an dem Video interessiert hat. (Zwischen den ausgewählten Bildern können Veränderungen fehlen. Soll genau geklärt werden, wie ein Titel erscheint oder in welche Richtung sich eine Person bewegt, kann ein KI-Assistent mit Videozugriff die Szene über den Originallink prüfen.)

## 3. Neue Beiträge ausgewählter Creator automatisch transkribieren

Füge einen Douyin-Creator hinzu, dessen neue Beiträge dich interessieren. Solange der Mac online ist, prüft er regelmäßig die öffentliche Profilseite. Beim ersten Abruf merkt er sich die vorhandenen Beiträge. Später entdeckte Videos werden automatisch transkribiert und im separaten Obsidian-Ordner „Abonnierte Creator“ gespeichert. Du musst die Links nicht einzeln kopieren. Bei einem zwanzigminütigen Video kannst du erst die Gliederung lesen und dann entscheiden, welchen Abschnitt du ansehen möchtest. (Die erste Version unterstützt manuell hinzugefügte Douyin-Creator. Ist der Mac längere Zeit offline, können Beiträge fehlen, die inzwischen aus der öffentlichen Liste verschwunden sind.)

## Funktionsweise

Der iPhone-Kurzbefehl legt den geteilten Link und deinen optionalen Hinweis im Obsidian-Ordner „Eingang für geteilte Inhalte“ ab. iCloud synchronisiert den Eintrag mit dem Mac. Der Hintergrunddienst verwendet zuerst abrufbare Untertitel der Plattform. Sind keine verfügbar, transkribiert er die Tonspur lokal mit Whisper `large-v3-turbo`. Auch die Texterkennung in Bildern und die erste Analyse von Videoszenen erfolgen auf dem Mac. Die Ergebnisse werden als Markdown-Notizen in Obsidian gespeichert. Download und Nutzung sind kostenlos. Bei der lokalen Standardverarbeitung fallen keine Transkriptionsgebühren oder Kosten für KI-Aufrufe an. (Bei Namen, Zahlen und Fachbegriffen können Erkennungsfehler auftreten. Über den Link in der Notiz lässt sich die Stelle im Original prüfen.)

## Hintergrund

Das Inspirationsarchiv soll Inhalte, die dir auf dem Smartphone begegnen, für die spätere Arbeit mit KI nutzbar machen. Wenn du etwa einen Artikel über Videoproduktion vorbereitest, kann ein KI-Assistent mit Zugriff auf deine Notizen die Aussagen mehrerer Creator zum selben Thema heraussuchen, ihre Vorgehensweisen vergleichen und die Originalvideos verlinken. Schon ein kurzer Gedanke, den du beim Speichern festhältst, kann dich beim nächsten Projekt zur passenden Quelle zurückführen.

## Ausblick

Eine automatische Kategorisierung und Kompatibilitätstests für Windows sind in Vorbereitung. Auch die Unterstützung von Android ist geplant. Als weitere Quellen kommen unter anderem X, YouTube, TikTok und Instagram sowie Toutiao, öffentliche WeChat-Konten und Zhihu infrage. Das sind erste Beispiele. Welche weiteren Plattformen hinzukommen, soll sich am tatsächlichen Bedarf orientieren.

Das Sammeln unterwegs soll auch mit künftigen Versionen unkompliziert bleiben. Hinweise dazu, aus welchen Quellen du Material übernehmen möchtest oder welcher Schritt noch zu umständlich ist, sind in den GitHub Issues willkommen. Sie helfen bei der Auswahl der nächsten Plattformen und Funktionen.

## Einrichtung

v0.1.0-alpha.1 ist die erste öffentliche Vorabversion. Das Downloadpaket verwendet derzeit chinesische Datei- und Oberflächennamen. Im Text stehen die deutschen Entsprechungen. Der folgende Tresorname muss für diese Version genau übernommen werden.

1. Installiere Obsidian auf beiden Geräten und aktiviere iCloud Drive mit demselben Apple Account. Erstelle oder öffne auf dem iPhone den Tresor `灵感与素材` („Inspiration und Material“) mit aktivierter Speicherung in iCloud. Sobald der Ordner im Finder unter iCloud Drive → Obsidian erscheint, öffne ihn auf dem Mac als Tresor.
2. Lade die ZIP-Datei auf den Mac, entpacke sie und öffne `一键配置.command` (Einrichtung per Doppelklick). Beim ersten Start werden mehrere GB an Werkzeugen und Modellen heruntergeladen. Falls macOS die Apple Command Line Tools anfordert, installiere sie und starte die Einrichtung erneut. Bestätige anschließend den Import des Kurzbefehls.
3. Aktiviere die iCloud-Synchronisierung für Kurzbefehle. Füge den synchronisierten Kurzbefehl auf dem iPhone unter Kontrollzentrum → Steuerelement hinzufügen → Kurzbefehle hinzu. Alternativ kannst du ihn direkt auf dem iPhone herunterladen. Probiere ein kurzes Bilibili-Video aus und prüfe nach der Verarbeitung den Ordner „Videoideen“. Um einem Douyin-Creator zu folgen, öffne `添加特别关注.command` (Creator hinzufügen) und füge die URL seiner öffentlichen Profilseite auf Douyin Jingxuan ein.

[Ausführliche Einrichtung und Fehlerbehebung auf Chinesisch](README.md#第一次使用) · [MIT-Lizenz](LICENSE)
