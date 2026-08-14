// Uebersetzungen. NUR Deutsch steht hier — die uebrigen vier liegen unter
// /static/i18n/<sprache>.json und werden nur geholt, wenn sie gebraucht werden. (#350)
//
// WARUM: Die Tabelle war 34 % dieser Datei, verteilt auf ZEHN Zeilen zu bis zu 8.166
// Zeichen. Jede Aenderung daran war ein Ganzzeilen-Konflikt — drei an einem Tag. Und
// jeder Besucher lud alle fuenf Sprachen, obwohl er eine liest: rund 61 der 76 KB waren
// tot. Ein Versuch, sie per Regex umzubrechen, zerschnitt einen Uebersetzungstext, der
// ein JSON-Beispiel enthaelt — deshalb hat NODE die Tabelle ausgewertet, nicht ein Muster.
//
// WARUM DEUTSCH BLEIBT: `t()` faellt auf `I18N.de` zurueck. Waere auch das nur geholt,
// zeigte die Oberflaeche bei einem fehlgeschlagenen Abruf nackte Schluessel.
//
// Only German is inlined; it is the fallback t() already uses, so a failed fetch shows
// real text instead of raw keys. Node evaluated the table — a regex split a value
// containing a JSON example.
// WARUM DEUTSCH HIER FEST DRINSTEHT und nicht wie die anderen vier nachgeladen wird:
// Es ist der Rueckfall fuer JEDEN fehlenden Schluessel (`t()` unten). Ein Nachladen waere
// eine Anfrage vor dem ersten Text.
//
// DESHALB GILT: Jeder Schluessel, den irgendeine Sprachdatei hat, MUSS auch hier stehen.
// `static/i18n/de.json` wird vom Browser NIE geholt — sie steht nicht in der Karte am
// <body>, und `i18nLaden()` kehrt fuer "de" sofort zurueck. Sie ist die Quelle fuer
// Uebersetzer. Ein Schluessel nur dort bedeutet: deutsche Nutzer sehen den BEZEICHNER.
// Genau so geschehen mit `stream_encrypted` und `stream_cia` aus #354. (#364)
//
// German is inlined because it is the fallback for every missing key. de.json is never
// fetched — a key that exists only there shows German users the raw key.
const I18N={de:{"nav_discover":"Entdecken","nav_requests":"Anfragen","nav_users":"👤 Benutzer","nav_settings":"Einstellungen","logout":"🚪 Abmelden","search_ph":"Spiel suchen … (Enter)","platforms":"Plattformen","all":"Alle","selected":"gewählt","hint_type":"Tippe einen Titel und drücke Enter.","loading_home":"Lade Startseite …","popular_on":"Beliebt auf","click_search":"klick zum Suchen","searching":"Suche läuft …","no_results":"Keine Treffer.","results":"Treffer","in_library":"✓ in Bibliothek","download":"⬇ Download","requested":"✓ angefragt","collection":"Sammlung","versions":"Versionen / Quellen","files":"Dateien","no_desc":"Keine Beschreibung verfügbar.","screenshots":"Screenshots","similar":"Ähnliche Spiele","series":"Reihe","because_you":"Weil du angefragt hast:","lib_grp_home":"Heimcomputer & frühe Konsolen","lib_grp_pc":"PC, DOS & Arcade","lib_grp_hand":"Handhelds & Kurioses","lib_grp_rest":"Ohne Zuordnung","no_requests":"Noch keine Anfragen.","approve":"Freigeben","deny":"Ablehnen","retry":"Erneut","reset":"Alle zurücksetzen","req_all":"Alle anfragen","flt_user":"Nutzer","flt_all":"Alle","wishlist":"Wunschliste","nav_coverage":"Abdeckung","nav_library":"Bibliothek","lib_hint":"Was tatsächlich da ist — nach Hersteller und System. Die Abdeckung daneben beantwortet die Gegenfrage: was fehlt.","lib_titles":"Titel","lib_owned":"vorhandene Titel","lib_none":"Keine Titel gefunden.","lib_empty":"Die Bibliothek ist leer oder noch nicht indiziert.","emu_install":"installieren","emu_needs_url":"Für diesen Emulator gibt es keine automatisch ermittelbare Quelle — URL in der .env des Streaming-Hosts eintragen.","emu_needs_url_kurz":"URL nötig","emu_rb_confirm":"{n} auf die vorherige Fassung zurücksetzen?","emu_update_one":"Nur diesen Emulator aktualisieren","emu_rb_title":"Eine Fassung zurück ({n} aufgehoben) — jetzt: {v}","emu_rb_failed":"Zurücksetzen fehlgeschlagen","emu_update":"Emulatoren aktualisieren","emu_nohost":"kein Streaming-Host erreichbar","emu_nolauncher":"kein Start-Dienst hinterlegt","emu_unreachable":"Start-Dienst nicht erreichbar","emu_running":"Aktualisierung läuft …","emu_none":"keine Emulatoren installiert","emu_ok":"zuletzt erfolgreich","emu_failed":"zuletzt fehlgeschlagen","fw_hint":"BIOS und Firmware liegen auf dem Streaming-Host, nicht in Romseerr. Was hier fehlt, endet im Stream als schwarzes Bild — deshalb steht es je Plattform.","fw_ready":"vollständig","fw_notinstalled":"Datei liegt bereit, ist im Emulator aber nicht eingespielt — einmalig dort installieren","fw_missing":"fehlt","fw_badsize":"Größe unerwartet — abgebrochener Download?","fw_upload":"Datei hochladen","fw_vendor":"beim Hersteller holen","fw_docs":"Anleitung","fw_nolauncher":"kein Start-Dienst hinterlegt — Firmware-Stand unbekannt","fw_fetching":"Hersteller-Download läuft …","fw_sending":"übertrage","fw_failed":"Übertragung fehlgeschlagen","stream":"Streamen","stream_seats":"{f} von {n} Plätzen frei","stream_single":"Einzelplatz — eine Sitzung gleichzeitig","stream_busy":"Belegt: {u} spielt gerade {g}","stream_stop":"Sitzung beenden","stream_not_in_lib":"Zum Streamen muss der Titel in der Bibliothek liegen.","stream_no":"Streamen gerade nicht möglich.","stream_running":"▶ läuft — Fenster geöffnet","stream_manual":"Desktop geöffnet — Titel dort starten","stream_failed":"Start fehlgeschlagen — Desktop geöffnet","stream_title":"Streaming-Host","stream_hint":"Für Plattformen, die der Browser nicht emulieren kann (PS2, GameCube, Wii, Switch). Der Emulator läuft auf dem Host, der Browser bekommt Bild und Ton. Ohne Start-Dienst öffnet Romseerr nur den Desktop.","stream_url2_l":"Browser-URL Platz 2 (optional)","stream_launch2_l":"Start-Dienst Platz 2","stream_seat2_hint":"Zweiter Platz — nur nötig, wenn der Stream-Host mit <code>--profile seat2</code> läuft. Dann können zwei Leute gleichzeitig spielen; Romseerr vergibt den ersten freien Platz.","stream_url_l":"Browser-URL des Hosts","stream_launch_l":"Start-Dienst (optional)","sec_outbound":"Ausgehende Anfragen","outbound_hint":"Webhook- und Katalog-URLs setzt der Nutzer. Standardmäßig lehnt Romseerr Ziele im privaten Netz, auf Loopback und Link-Local ab — sonst könnte jeder angemeldete Nutzer den Server auf interne Adressen schicken. Wer sein Benachrichtigungsziel im selben Netz betreibt, muss das hier ausdrücklich erlauben.","outbound_allow":"Ziele im privaten Netz erlauben","play":"Im Browser spielen","play_no_romm":"Spielen nicht möglich — RomM ist nicht verbunden.","play_no_core":"Diese Plattform lässt sich im Browser nicht emulieren.","play_not_in_lib":"Zum Spielen muss der Titel in der Bibliothek liegen.","play_too_large":"Zu groß für den Browser (Grenze {mb} MB).","play_no_title":"Kein Titel.","play_bios":"braucht BIOS","play_romset":"Arcade: nur mit passendem Romset","cat_title":"Filehoster-Kataloge (experimentell)","cat_hint":"Katalog-JSON-Quellen, eine URL je Zeile. Bewusst NICHT mitgeliefert — die Quellen bestimmt der Betreiber. Format: {name, downloads:[{title,uris,uploadDate,fileSize}]}.","cat_urls":"Quell-URLs","cat_refresh":"Jetzt holen","cat_none":"keine Quelle hinterlegt — der Filehoster-Weg ist inaktiv","cat_items":"Einträge insgesamt","cfg_warn":"Konfiguration","cfg_warn_hint":"Ein Weg ist nicht benutzbar — Downloads darüber starten gar nicht erst.","notif_maillog":"Mail-Protokoll","conn_scraper":"Scraper / Cover-Quellen","sub_an":"aktiv","sub_da":"eingerichtet, aber aus","sub_leer":"nicht eingerichtet","details":"Details","nav_lists":"Meine Listen","favourites":"Favoriten","favourite":"Favorit","fav_empty":"Noch keine Favoriten.","fav_remove":"Entfernen","fav_hint":"Titel, die du schnell wiederfinden willst. Anders als die Wunschliste verschwinden sie nie von selbst.","wl_hint_head":"Wunschliste — was du noch nicht hast","flt_active":"aktiv","flt_done":"erledigt","flt_failed":"fehlgeschlagen","flt_leer":"In diesem Filter ist nichts.","flt_denied":"abgelehnt","cov_measurable":"{n} von {m} Konsolen messbar","cov_method":"Summe besessen ÷ Summe bekannt — nicht das Mittel der Prozente, das gäbe kleinen Systemen dasselbe Gewicht wie großen.","bl_hint":"<b>Teilstring, keine Regex.</b> Ein Eintrag greift, wenn er irgendwo im <b>Titel</b> vorkommt — Groß-/Kleinschreibung egal, Sonderzeichen wie <code>.</code> oder <code>*</code> stehen für sich selbst. Geprüft wird <b>nur der Titel</b>, nicht Dateiname, Release-Gruppe oder Plattform. Die Regel wirkt in Suche, Entdecken und Empfehlungen und <b>lehnt neue Anfragen ab</b>. Einen <b>bereits laufenden Auftrag hält sie nicht an</b>, und schon vorhandene Dateien entfernt sie nicht. Sie gilt für <b>alle Nutzer</b> dieser Instanz.","rate_title":"Bewertung","rate_mine":"deine Bewertung","rate_others":"andere","rate_clear":"zurücknehmen","comments":"Kommentare","comments_none":"Noch keine Kommentare.","jd_hint":"Drei Sichten auf dieselbe Übergabe: die ersten beiden sieht Romseerr, die dritte JDownloader. Leer = Standard.","jd_watch":"Watch-Ordner (Romseerr schreibt)","jd_out":"Fertig-Ordner (Romseerr liest)","jd_base":"Download-Basis (JDownloader-Sicht)","var_prefs":"Fassungen (Region/Sprache)","var_region_order":"Regionsreihenfolge — die Reihenfolge ist die Vorliebe","var_lang":"Bevorzugte Sprache","var_prerelease":"Beta/Prototyp/Demo zulassen","var_unspec":"unspezifiziert","var_preferred":"bevorzugt","var_hint":"Instanzweiter Rückfall für Nutzer, die selbst nichts eingestellt haben. Region ändert Inhalt (Sprache, Schwierigkeit, Zensur, 50/60 Hz) — das ist keine Qualitätsleiter, deshalb wird nach dieser Reihenfolge gewählt und nicht sortiert.","var_of":"Fassung","ra_achievements":"Achievements","ra_points":"Punkte","ra_earned":"erreicht","ra_user":"RetroAchievements-Konto (optional)","ra_refresh":"Sets holen","ra_sets":"Sets","ra_nokey":"kein API-Key hinterlegt","ra_unmapped":"ohne Konsolen-Zuordnung","ra_only":"nur mit Achievements","cov_of":"von","cov_src":"Quelle","cov_asof":"Stand","cov_files":"Dateien","cov_missing":"fehlende Titel","cov_refresh":"Katalog aktualisieren","cov_nosnap":"keine Momentaufnahme — Katalog noch nicht geholt","cov_nosource":"keine Katalogquelle für diese Plattform","cov_basis":"Grundlage ist eine Momentaufnahme aus {src} (max. {max} Titel je Plattform). Metadatensätze sind sich uneins, was als eigener Titel zählt — die Prozentzahl ist eine Orientierung, kein Messwert.","cov_search":"Suchen","cov_none":"Nichts fehlt (oder kein Katalog).","cov_filter":"Filtern …","cov_filter_do":"Filtern","cov_wish_sel":"Auswahl auf die Wunschliste","wl_import":"Import","wl_imp_hint":"Liste einfügen oder Datei wählen (TXT/CSV) — ein Titel je Zeile, optional Titel;Plattform. Nichts wird geschrieben, bevor du die Vorschau bestätigst.","wl_imp_example":"Beispieldatei herunterladen","wl_imp_ph":"Chrono Trigger\nSuper Metroid;snes","wl_imp_preview":"Vorschau","wl_imp_apply":"Übernehmen","wl_imp_none":"Nichts ausgewählt.","wl_imp_done":"{a} übernommen, {s} übersprungen.","wl_imp_trunc":"Nur die ersten {n} Zeilen werden geprüft.","wl_imp_toobig":"Datei zu groß (max. 200 kB).","wl_imp_nocheck":"Ohne IGDB-Zugang kein Katalogabgleich — Einträge werden ungeprüft übernommen.","wl_s_matched":"getroffen","wl_s_ambiguous":"mehrdeutig","wl_s_notfound":"nicht gefunden","wl_s_duplicate":"schon gemerkt","wl_s_inlib":"schon vorhanden","wl_s_unverified":"ungeprüft","add_wishlist":"⭐ Merken","wl_added":"⭐ gemerkt","wl_empty":"Wunschliste leer.","wl_remove":"Entfernen","users":"Benutzer","new_user":"Neuen Benutzer anlegen","create":"Anlegen","del":"Löschen","autoapprove":"Auto-Freigabe","role_user":"Nutzer","role_admin":"Admin","username":"Benutzername","password":"Passwort","notif_discord":"Benachrichtigungen — Discord","active":"aktiv","test":"Test","save":"Speichern","saved":"gespeichert ✓","test_sent":"Test gesendet ✓","webhook_ph":"Discord Webhook-URL","st_pending":"⏳ Wartet auf Freigabe","st_queued":"Angefragt","st_downloading":"Lädt…","st_importing":"Wird verarbeitet","st_done":"✅ Verfügbar","st_error":"Fehler","st_denied":"Abgelehnt","st_exists":"vorhanden","settings":"Einstellungen","sec_general":"Allgemein","sec_notif":"Benachrichtigungen","sec_users":"Benutzer","sec_services":"Dienste","sec_about":"Über","app_name":"App-Name","default_lang":"Standardsprache","refresh":"Aktualisieren","version":"Version","about_build":"Build","about_no_build":"Herkunft unbekannt — diese Instanz kann nicht sagen, ob sie dem Quellstand entspricht.","upd_avail":"Update verfügbar:","upd_current":"aktuell","about_txt":"Selbstgebauter Seerr-Klon für ROMs.","wiz_welcome":"Willkommen bei Romseerr","wiz_welcome_txt":"Dieser Assistent verbindet dich Schritt für Schritt mit den Diensten des Stacks (SABnzbd, Prowlarr, IGDB, RomM). Jeden Schritt kannst du testen oder überspringen.","wiz_done":"Fertig!","wiz_done_txt":"Die Grundkonfiguration steht. Alles lässt sich später unter Einstellungen → Verbindungen anpassen.","wiz_next":"Weiter","wiz_back":"Zurück","wiz_skip":"Überspringen","wiz_finish":"Loslegen","wiz_step":"Schritt","wiz_reopen":"Assistent erneut öffnen","about_lib":"Bibliothek","about_titles":"Titel","about_platforms":"Plattformen","about_jobs":"Anfragen","about_active":"aktiv","about_links":"Links","about_feat":"Funktionen","about_feat_txt":"Suche über Archive.org + Usenet, Dedup, Discover, Anfragen mit Freigabe, Benutzer & Rechte, Kontingente, Benachrichtigungen (Discord/Telegram/E-Mail/Web-Push), Probleme, PWA, API.","about_stack":"Stack","about_stack_txt":"Orchestriert Prowlarr, SABnzbd, JDownloader und RomM. Verbindungen in den Einstellungen konfigurierbar.","about_license":"Lizenz: MIT","sec_maint":"Logs & Wartung","exp_title":"Export / Import","exp_hint":"Sichert Einstellungen, Benutzer & Rechte, Anfragen und Wunschlisten als JSON. Ohne Passphrase bleiben Geheimnisse (Kennwörter, API-Keys, Webhook-URLs) AUSSEN VOR — mit Passphrase werden sie verschlüsselt beigelegt. Dieselbe Passphrase wird beim Import gebraucht.","exp_pass":"Passphrase","exp_pass_ph":"leer = ohne Geheimnisse","exp_do":"Exportieren","exp_merge":"Zusammenführen","exp_replace":"Ersetzen","imp_do":"Importieren","exp_done_plain":"Exportiert (ohne Geheimnisse).","exp_done_enc":"Exportiert (Geheimnisse verschlüsselt).","imp_nofile":"Keine Datei gewählt.","imp_badjson":"Datei ist kein gültiges JSON.","imp_conf_merge":"Import zusammenführen? Bestehende Werte werden überschrieben, nicht genannte bleiben.","imp_conf_replace":"ERSETZEN? Benutzer, Anfragen und Wunschlisten werden vollständig durch die Datei ersetzt.","imp_done":"Importiert:","logs":"Protokoll","clear_cache":"Cache leeren","reindex":"Neu indexieren","clear_finished":"Fertige entfernen","done_word":"Erledigt","lbl_jobs":"Anfragen","lbl_lib":"Bibliothek","sec_conn":"Verbindungen","reveal":"Klartext anzeigen","tls_hint":"Cert + Schlüssel (PEM) hinterlegen — die App startet dann zusätzlich einen HTTPS-Listener auf dem gewählten Port (Neustart nötig). Für Web-Push/PWA ohne separaten Reverse-Proxy.","tls_none":"kein Zertifikat hinterlegt","tls_expires":"gültig bis","tls_key_note":"privater Schlüssel — wird nie angezeigt","tls_restart":"Container neu starten zum Aktivieren","conn_hint":"Leere Felder nutzen den Wert aus der Umgebung (.env). Secrets sind maskiert — leer lassen behält den bestehenden Wert.","un_check":"Usenet-Weg prüfen","un_hint":"Misst die Kette Suche → Kategorie → Warteschlange → Einsammelordner, ohne etwas herunterzuladen. Die letzte Zeile zeigt beide Sichten auf denselben Ordner — laufen sie auseinander, läuft der Download durch und wird trotzdem nie gefunden.","un_search":"Suche über Prowlarr","un_cat":"SAB-Kategorie","un_queue":"Warteschlange","un_collect":"Einsammelordner","un_indexer":"Indexer","un_grab":"Der Indexer-Test holt je Indexer EINE Datei ab — das zählt dort als Abruf gegen ein Stundenlimit.","lo_title":"Liegengebliebene Downloads","lo_hint":"Was ein fehlgeschlagener Import nicht verwerten konnte, bleibt liegen, statt gelöscht zu werden — sonst wäre der Download verloren und die Ursache nicht mehr nachsehbar. Aufräumen musst du selbst; älter als die eingestellte Frist verfällt von allein.","lo_none":"nichts liegen geblieben","lo_remove":"Entfernen","lo_removeall":"Alle entfernen","lo_days":"Verfallsfrist (Tage, 0 = aus)","lo_confirm":"Diesen Download endgültig löschen?","lo_confirmall":"ALLE liegengebliebenen Downloads endgültig löschen?","lo_age":"Tage alt","reimp":"Erneut einlesen","reimp_hint":"Liest die bereits geladenen Dateien noch einmal ein — ohne neuen Download.","reimp_gone":"Dateien sind nicht mehr da","reimp_started":"Wird eingelesen …","del_job":"Entfernen","del_confirm":"Diese Anfrage aus der Liste entfernen?","del_withfiles":"Der heruntergeladene Ordner liegt noch da. Auch die Dateien löschen?\n\nOK = Anfrage und Dateien löschen\nAbbrechen = nur die Anfrage entfernen (Dateien bleiben liegen)","del_left":"Anfrage entfernt — die Dateien bleiben liegen (siehe Wartung)","clear_group":"Angezeigte entfernen","clear_all_final":"Erledigte, fehlgeschlagene und abgelehnte entfernen","try_n":"Versuch","retry_other":"Erneut · andere Quelle","retry_other_hint":"Dieselbe Quelle ist zweimal gescheitert — der nächste Versuch nimmt eine andere.","exhausted":"Alle Quellen versucht — keine andere übrig.","stream_ambiguous":"Dieser Titel liegt auf mehreren Plattformen — welche ist gemeint?","jd_probe":"Übergabe ausprobieren","jd_probe_hint":"Legt einen wirkungslosen Auftrag in den Watch-Ordner und wartet, ob JDownloader ihn abholt. Beantwortet „hört jemand zu“ — nicht, ob ein Download danach wirklich anläuft. Dauert bis zu 30 s und hinterlässt einen deaktivierten Eintrag im Linksammler.","jd_probe_run":"läuft — bis zu 30 s …","stream_badtoken":"Der Start-Dienst weist Romseerr ab: das Token stimmt nicht überein. Der Host läuft — es muss auf BEIDEN Seiten dasselbe stehen (Einstellungen → Streaming-Host und STREAM_AGENT_TOKEN auf dem Host).","profile":"Profil","display_name":"Anzeigename","email":"E-Mail","language":"Sprache","design":"Design","default_design":"Standard-Design","d_seerr":"Seerr","d_glass":"Glas","d_clean":"Klar","avatar":"Avatar","pwebhook":"Persönlicher Discord-Webhook","change_pw":"Passwort ändern","cur_pw":"Aktuelles Passwort","new_pw":"Neues Passwort","choose_img":"Bild wählen","saved_ok":"gespeichert ✓","blocklist":"Sperrliste","add_btn":"Hinzufügen","pattern_ph":"Stichwort/Muster im Titel","nav_issues":"Probleme","nav_messages":"Nachrichten","msg_to":"An","msg_none":"Noch keine Nachrichten.","msg_ph":"Nachricht schreiben …","msg_send":"Senden","msg_hint":"Strg+Enter sendet","msg_nousers":"Keine anderen Benutzer.","req_for":"Anfrage für","req_self":"mich selbst","issues":"Probleme","report_issue":"Problem melden","issue_msg":"Beschreibung","close_btn":"Schließen","st_open":"offen","st_closed":"geschlossen","submit":"Absenden","issue_type":"Art","comment_ph":"Kommentar schreiben …","comment_send":"Senden","push_enable":"🔔 Push aktivieren","push_disable":"🔕 Push deaktivieren","push_unsupported":"Push nicht verfügbar (HTTPS nötig)","push_denied":"Erlaubnis verweigert","push_on":"Push aktiviert ✓","push_off":"Push deaktiviert","stream_encrypted":"Dieses Abbild ist verschlüsselt — der Emulator spielt nur entschlüsselte Dumps.","stream_cia":"CIA-Dateien sind Installationspakete und starten nicht direkt.","stream_cia_update":"Das ist ein Update, kein Spiel — es gehört zu einem anderen Titel und startet auch installiert nicht.","stream_cia_dlc":"Das ist ein Zusatzinhalt (DLC), kein eigenständiges Spiel.","stream_cia_broken":"Diese CIA lässt sich nicht lesen — der Titelkopf fehlt oder ist beschädigt.","plat_unknown":"Plattform unbekannt","needs_ia_login":"Konto nötig","ia_hint":"Manche Archive.org-Titel liegen in der Sammlung `loggedin` und brauchen ein Konto — ohne eines antwortet der Download mit HTTP 401. Hier gehört KEIN Passwort hin, sondern das Schlüsselpaar von archive.org/account/s3.php: einzeln widerrufbar, ohne Sitzung, die still abläuft.","job_open_card":"Zur Karte des Spiels","job_no_card":"Zu diesem Titel gibt es keine Karte.","job_lookup_failed":"Die Karte konnte nicht geladen werden.","sec_drop":"Einwurf","drop_hint":"Der Einwurfordner nimmt ROMs auf, die nicht über eine Anfrage kommen — eine ganze Sammlung, ein Ordner vom Stick. <b>Diese Ansicht verschiebt nichts</b>, sie rechnet nur durch, was passieren würde. Angefasst wird eine Datei erst, wenn sie zwei Durchgänge lang unverändert geblieben ist — ein noch laufender Upload bleibt also liegen. Was sich keiner Plattform zuordnen lässt, wandert nach <code>.unsortiert</code>, statt geraten zu werden.","drop_off":"Kein Einwurfordner eingehängt — die Funktion ist nicht eingerichtet. Erwartet wird:","drop_every":"wird alle {n} Minuten von selbst geprüft","drop_ready":"Wird einsortiert","drop_stuck":"Bleibt liegen","drop_none":"Der Ordner ist leer.","drop_more":"… und {n} weitere","drop_scan":"Jetzt einlesen","drop_running":"läuft …","drop_done":"{a} einsortiert, {o} liegen geblieben","stream_nsp_update":"Das ist ein Update, kein Spiel — es gehört zu einem anderen Titel und startet auch installiert nicht.","stream_nsp_dlc":"Das ist ein Zusatzinhalt (DLC), kein eigenständiges Spiel.","stream_wiiu_update":"Das ist ein Update, kein Spiel — es patcht ein Basisspiel, das hier nicht liegt.","stream_wiiu_dlc":"Das ist ein Zusatzinhalt (DLC), kein eigenständiges Spiel.","sec_organize":"Bibliothek organisieren","org_start_dry":"Testlauf","org_start_real":"Umbau starten","org_stop":"Anhalten","org_all":"ganze Bibliothek","org_platform_l":"Plattform","org_confirm":"Der Umbau verschiebt Dateien in der Bibliothek. Jede Aktion steht im Protokoll und lässt sich damit zurücknehmen. Jetzt starten?","org_started":"gestartet","org_stopped":"angehalten","org_busy":"Es läuft bereits ein Umbau.","org_failed":"Start fehlgeschlagen","org_notool":"Die Bibliothekswerkzeuge fehlen im Abbild.","org_restart_note":"Ein Neustart des Containers bricht einen laufenden Umbau ab. Das kostet keine Arbeit: Der nächste Lauf setzt dort fort, wo dieser stand.","org_own":"aus dieser Oberfläche gestartet","org_foreign":"außerhalb gestartet — von hier nicht anzuhalten","org_dry_note":"Ein Testlauf verschiebt nichts und hinterlässt keinen Wiederaufsetzpunkt.","org_output":"Ausgabe","org_hint":"Der Umbau sortiert die Bibliothek so, dass RomM, Romseerr und RetroNAS dasselbe sehen. <b>Diese Ansicht startet nichts</b> — sie zeigt, was gerade läuft und was zuletzt lief. Ein vollständiger Lauf dauert über dieser Bibliothek Stunden; jede Aktion steht als Zeile in einem Protokoll und lässt sich damit zurücknehmen.","org_full":"Vollständiger Umbau","org_beiwerk":"Nur Beiwerk einsammeln","org_running":"läuft","org_finished":"abgeschlossen","org_aborted":"abgebrochen","org_none":"Für diese Bibliothek ist noch kein Umbau gelaufen.","org_nodir":"Kein Arbeitsverzeichnis vorhanden — es entsteht beim ersten echten Lauf.","org_elapsed":"Laufzeit","org_remaining":"Restzeit (geschätzt)","org_current":"gerade","org_platforms":"Plattformen","org_files":"Dateien","org_failed":"mit Fehler","org_logs":"Protokolle — jedes ist ein Rückweg","org_undo":"Rückweg","org_nologs":"Noch keine Protokolle.","org_est_hint":"Die Restzeit rechnet aus dem bisherigen Tempo hoch. Plattformen sind sehr verschieden groß, sie ist deshalb eine Orientierung und kein Versprechen.","stream_wiiu_system":"Das ist ein Systemtitel der Konsole, kein Spiel."}};

// Die aktive Sprache nachladen. Fuer Deutsch faellt der Abruf ganz weg.
// Das Ergebnis wird gemerkt: ein Sprachwechsel hin und zurueck holt nicht erneut.
async function i18nLaden(l){
 if(l==="de"||I18N[l])return;
 try{
  // Die Adresse kommt aus dem Datenattribut am <body>; sie ist inhaltsgehasht und
  // wird `immutable` ausgeliefert. Ein fester Pfad wie /static/... gaebe es nicht:
  // statische Dateien laufen hier ausschliesslich ueber /assets/<hash>/.
  let karte=JSON.parse(document.body.dataset.i18nSrc||"{}");
  if(!karte[l])return;
  let r=await fetch(karte[l]);
  if(r.ok)I18N[l]=await r.json();
 }catch(e){/* t() faellt auf Deutsch zurueck — sichtbar, aber nicht kaputt */}
}
let LANG=localStorage.getItem('lang')||'de';
// Design (Look) so früh wie möglich setzen, um ein Umflackern beim Laden zu vermeiden.
const DESIGNS=['seerr','glass','clean'];
function applyDesign(dz){if(!DESIGNS.includes(dz))dz='seerr';document.documentElement.dataset.design=dz;localStorage.setItem('design',dz);
 document.querySelectorAll('.dpick').forEach(e=>e.classList.toggle('on',e.dataset.d==dz));}
applyDesign(localStorage.getItem('design')||'seerr');
function t(k){return (I18N[LANG]&&I18N[LANG][k])||I18N.de[k]||k;}
// Sprachen mit Flagge UND Name (#206). Eine Flagge allein ist ein Land, keine Sprache —
// Englisch unter 🇬🇧 liest sich für Amerikaner falsch, Spanisch unter 🇪🇸 für Lateinamerika.
// Im Aufklappmenü ist Platz für beides; eingeklappt genügt die Flagge.
const SPRACHEN=[['de','🇩🇪','Deutsch'],['en','🇬🇧','English'],['fr','🇫🇷','Français'],
                ['es','🇪🇸','Español'],['it','🇮🇹','Italiano']];
async function setLang(l){LANG=l;localStorage.setItem('lang',l);
 // Erst die Tabelle holen, dann anwenden — sonst zeigt die Oberflaeche kurz Deutsch
 // und springt danach um. Fuer Deutsch faellt der Abruf weg, es ist also kein Warten.
 await i18nLaden(l);
 applyI18n();
 zeichneKopf();
 if(cur=='s'&&!document.getElementById('q').value.trim())loadDiscover();if(cur=='j')loadJobs();}
// --- Kopfleiste rechts: Sprache und Person (#206) ---
function toggleMenu(id,ev){
 if(ev)ev.stopPropagation();
 let m=document.getElementById(id);if(!m)return;
 let box=m.parentElement,auf=box.classList.contains('auf');
 closeMenus();
 if(!auf){box.classList.add('auf');let b=box.querySelector('button');if(b)b.setAttribute('aria-expanded','true');}}
function closeMenus(){document.querySelectorAll('.aufklapp.auf').forEach(b=>{
 b.classList.remove('auf');let x=b.querySelector('button');if(x)x.setAttribute('aria-expanded','false');});}
// Ein Menue, das nur der erneute Klick auf denselben Knopf schliesst, aergert taeglich.
document.addEventListener('click',e=>{if(!e.target.closest('.aufklapp'))closeMenus();});
// EIN Handler für Escape, nicht zwei, die um dieselbe Taste konkurrieren (#226).
// Reihenfolge: erst das Menü, dann das Fenster darunter — sonst verliert man mit einem
// Tastendruck beides und damit seinen Platz.
document.addEventListener('keydown',e=>{
 if(e.key!=='Escape')return;
 if(document.querySelector('.aufklapp.auf')){closeMenus();return;}
 let m=document.getElementById('modal');
 if(m&&m.style.display==='block')closeModal();});

// --- Fokus im Dialog halten (#258) ---
// Der Dialog liegt als `fixed`-Overlay über dem Kopf und schluckt Mausklicks dorthin — der
// FOKUS ging aber weiterhin hin. Mit Tab ließ sich hinter die modale Fläche greifen und ein
// Menü bedienen, das Mausnutzer nicht einmal anklicken können. In #228 im Browser gemessen:
// `elementFromPoint` auf dem Menüknopf lieferte bei offenem Dialog `#modal`, `focus()` auf
// denselben Knopf gelang trotzdem.
//
// EN: the dialog covers the header and swallows clicks, but focus still reached it, so
// keyboard users could operate controls mouse users cannot even click.
const FOKUSSIERBAR='a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
let _fokusVorDialog=null;
function modalOffen(){let m=document.getElementById('modal');return !!(m&&m.style.display==='block');}
function modalFokusListe(){
 let m=document.getElementById('modal');if(!m)return [];
 return [...m.querySelectorAll(FOKUSSIERBAR)].filter(el=>el.offsetParent!==null);}
// Tab sauber im Kreis führen — sonst käme Shift+Tab am ersten Element wieder beim ersten an.
document.addEventListener('keydown',e=>{
 if(e.key!=='Tab'||!modalOffen())return;
 let liste=modalFokusListe();if(!liste.length)return;
 let erst=liste[0],letzt=liste[liste.length-1];
 if(e.shiftKey&&(document.activeElement===erst||!document.getElementById('modal').contains(document.activeElement))){
  e.preventDefault();letzt.focus();
 }else if(!e.shiftKey&&document.activeElement===letzt){
  e.preventDefault();erst.focus();}});
// Netz für alles andere (Klick, programmatischer Fokus): landet der Fokus draußen, kommt er zurück.
document.addEventListener('focusin',e=>{
 if(!modalOffen())return;
 let m=document.getElementById('modal');
 if(m.contains(e.target))return;
 let liste=modalFokusListe();if(liste.length)liste[0].focus();});
// Wer den Dialog geöffnet hat, wird beim Öffnen gemerkt — dorthin geht der Fokus zurück.
// Über einen Beobachter statt in jedem der vier Öffner: eine Stelle, die nicht vergessen
// werden kann, wenn ein fünfter dazukommt.
function fokusWaechterStarten(){
 let m=document.getElementById('modal');if(!m)return;
 let warOffen=modalOffen();
 new MutationObserver(()=>{
  let jetzt=modalOffen();
  if(jetzt&&!warOffen){
   _fokusVorDialog=document.activeElement;
   let liste=modalFokusListe();if(liste.length)liste[0].focus();}
  warOffen=jetzt;
 }).observe(m,{attributes:true,attributeFilter:['style']});}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',fokusWaechterStarten);
else fokusWaechterStarten();
function zeichneKopf(){
 let lb=document.getElementById('langbtn'),lm=document.getElementById('langmenu');
 if(lb&&lm){
  let akt=SPRACHEN.find(x=>x[0]===LANG)||SPRACHEN[0];
  lb.innerHTML=akt[1]+' <span style="opacity:.7">▾</span>';
  lb.title=akt[2];
  lm.innerHTML=SPRACHEN.map(x=>`<a class="mitem${x[0]===LANG?' on':''}" onclick="closeMenus();setLang('${x[0]}')">${x[1]} ${x[2]}</a>`).join('');}
 let ub=document.getElementById('userbtn');
 if(ub&&window._who)ub.innerHTML=window._who;}
function applyI18n(){
 document.querySelectorAll('[data-i18n]').forEach(e=>e.textContent=t(e.dataset.i18n));
 document.querySelectorAll('[data-i18n-ph]').forEach(e=>e.placeholder=t(e.dataset.i18nPh));
 updateFLabel();}
let cur='s';
// --- Verlauf und Adressen (#194) ---
// Die App hatte KEINE Vorstellung von Navigation: kein pushState, kein popstate, kein
// Hash. Browser-Zurück verliess damit die Anwendung (auf dem Telefon IST Zurück die
// Navigation), ein Neuladen landete immer auf Entdecken, und nichts war verlinkbar.
// Statt eines Zurück-Knopfes, der das nur überdeckt, bekommen die Ansichten eine
// Adresse — dann macht der Browser von sich aus das Richtige.
const ROUTEN={s:'discover',j:'requests',set:'settings',issues:'issues',msg:'messages',cov:'coverage',lists:'lists',lib:'library'};
const ROUTEN_UM=Object.fromEntries(Object.entries(ROUTEN).map(([k,v])=>[v,k]));
// Reine Funktion, absichtlich ohne DOM: so ist sie prüfbar, ohne die halbe Oberfläche
// nachzubauen. Gibt {view, detail} zurück; detail ist null oder das Nötigste, um
// openDetail() nach einem Neuladen erneut aufzurufen.
function routeParse(hash){
 let h=String(hash||'').replace(/^#\/?/,'');
 if(!h)return{view:'s',detail:null};
 let [pfad,frage]=h.split('?');
 let teile=pfad.split('/').filter(Boolean);
 if(teile[0]==='title'&&teile.length>=3){
  let p=new URLSearchParams(frage||'');
  return{view:p.get('v')&&ROUTEN_UM[p.get('v')]||'s',
         detail:{source:decodeURIComponent(teile[1]),ref:decodeURIComponent(teile.slice(2).join('/')),
                 title:p.get('t')||'',platform_slug:p.get('p')||''},sec:'',sub:''};
 }
 // Einstellungen tragen ihren Bereich und ihre Unterseite in der Adresse (#202): eine
 // Unterseite ist damit verlinkbar und ueberlebt ein Neuladen — vorher war das eine
 // Modulvariable, die beim ersten F5 verschwand.
 if(teile[0]==='settings')return{view:'set',detail:null,sec:teile[1]||'',sub:teile[2]||''};
 return{view:ROUTEN_UM[teile[0]]||'s',detail:null,sec:'',sub:''};
}
function routeBauen(v,detail,sec,sub){
 if(detail)return`#/title/${encodeURIComponent(detail.source||'')}/${encodeURIComponent(detail.ref||'')}`+
   `?v=${ROUTEN[v]||'discover'}&t=${encodeURIComponent(detail.title||'')}&p=${encodeURIComponent(detail.platform_slug||detail.platform||'')}`;
 if(v==='set'&&sec)return'#/settings/'+sec+(sub?'/'+sub:'');
 return'#/'+(ROUTEN[v]||'discover');
}
// Setzt die Adresse, ohne die Ansicht erneut zu zeichnen. `ersetzen` für den ersten
// Aufruf beim Start — sonst läge ein leerer Eintrag vor der Startseite im Verlauf.
let ROUTE_STUMM=false;
// Wie viele Verlaufseintraege haben WIR angelegt. Ohne das weiss `closeModal` nicht, ob
// ein `history.back()` zur vorigen Ansicht fuehrt oder aus Romseerr hinaus: Wer einen
// Titel-Link direkt oeffnet, hat genau einen Eintrag — davor liegt fremdes Gebiet. (#226)
let EIGENE_SCHRITTE=0;
function routeSetzen(v,detail,ersetzen,sec,sub){
 let neu=routeBauen(v,detail,sec,sub);
 if(location.hash===neu)return;
 ROUTE_STUMM=true;
 try{
  if(ersetzen)history.replaceState({v,detail},'',neu);
  else{history.pushState({v,detail},'',neu);EIGENE_SCHRITTE++;}
 }finally{setTimeout(()=>{ROUTE_STUMM=false;},0);}
}
function routeAnwenden(){
 let {view,detail,sec,sub}=routeParse(location.hash);
 if(view==='set'&&sec){SETSEC=sec;SETSUB=sub||'';}
 zeige(view);
 if(detail&&detail.ref)openDetail(detail,true);
 else closeModal(true);
}
window.addEventListener('popstate',()=>{EIGENE_SCHRITTE=Math.max(0,EIGENE_SCHRITTE-1);if(!ROUTE_STUMM)routeAnwenden();});
window.addEventListener('hashchange',()=>{if(!ROUTE_STUMM)routeAnwenden();});

// Die Menuepunkte sind echte Verweise mit `href`, damit sie eine Rolle haben, in der
// Tab-Reihenfolge stehen und von Screenreadern angesagt werden (#329). Zuvor waren es
// `<a>` OHNE `href` — gemessen: 0 von 7 per Tastatur erreichbar.
//
// Der Klick laeuft weiter ueber `show()` statt ueber die Navigation des Browsers, weil
// `routeSetzen` mit `EIGENE_SCHRITTE` mitzaehlt, wie viele History-Eintraege die App
// selbst gesetzt hat; davon haengt ab, ob das Schliessen eines Dialogs `history.back()`
// benutzen darf. Wuerde der Browser selbst navigieren, liefe dieser Zaehler aus dem Tritt.
// `return false` unterdrueckt deshalb die Standardnavigation — der `href` bleibt fuer
// Fokus, Rolle und „in neuem Tab oeffnen" wirksam.
//
// The entries are real links so they have a role and a tab position; the click still goes
// through show() because routeSetzen tracks how many history entries the app pushed, which
// decides whether closing a dialog may use history.back().
function navGeh(v){show(v);return false;}
function show(v){zeige(v);routeSetzen(v,null,false,v==='set'?SETSEC:'',v==='set'?SETSUB:'');}
function zeige(v){cur=v;
 document.getElementById('discview').style.display=v=='s'?'':'none';
 document.getElementById('jobs').style.display=v=='j'?'block':'none';
 document.getElementById('settings').style.display=v=='set'?'block':'none';
 document.getElementById('issues').style.display=v=='issues'?'block':'none';
 document.getElementById('messages').style.display=v=='msg'?'block':'none';
 document.getElementById('coverage').style.display=v=='cov'?'block':'none';
 document.getElementById('library').style.display=v=='lib'?'block':'none';
 document.getElementById('lists').style.display=v=='lists'?'block':'none';
 document.getElementById('nS').classList.toggle('on',v=='s');
 document.getElementById('nJ').classList.toggle('on',v=='j');
 document.getElementById('nI').classList.toggle('on',v=='issues');
 let nM=document.getElementById('nM');if(nM)nM.classList.toggle('on',v=='msg');
 let nL=document.getElementById('nL');if(nL)nL.classList.toggle('on',v=='lib');
 document.getElementById('nSet').classList.toggle('on',v=='set');
 // `class=on` ist nur Farbe. Welcher Punkt der aktuelle ist, muss auch angesagt
 // werden — dafuer `aria-current`, sonst hoert ein Screenreader sieben
 // gleichwertige Verweise. / class=on is colour only; aria-current carries the
 // state to assistive technology.
 document.querySelectorAll('a.nav').forEach(a=>{
  if(a.classList.contains('on'))a.setAttribute('aria-current','page');
  else a.removeAttribute('aria-current');});
 if(v=='j')loadJobs();if(v=='set')openSettingsView();
 if(v=='issues'){loadIssues(window._ipref);window._ipref=null;}
 let nC=document.getElementById('nC');if(nC)nC.classList.toggle('on',v=='cov');
 if(v=='msg')loadMessages();if(v=='cov')loadCoverage();if(v=='lib')loadLibrary();if(v=='lists')loadLists();}
// --- Abdeckung je Plattform: „was fehlt mir" statt „was habe ich" (#78) ---
// Jede Zahl traegt Quelle + Stand — eine nackte Prozentzahl waere hier irrefuehrend.
// Abdeckung nach Hersteller (#199). Vorher: 26 gleich breite Zeilen hintereinander, ohne
// jede Ebene darüber — nichts sagte, wie vollständig „Nintendo" ist, nur wie vollständig
// die SNES. Die Gruppierung lag die ganze Zeit daneben (PLATFORMS, dieselbe wie im Filter).
//
// DIE ZAHL AUF DER HERSTELLERKARTE ist bewusst NICHT das Mittel der Prozente — das gäbe
// dem Virtual Boy dasselbe Gewicht wie der SNES. Gerechnet wird Summe besessen gegen Summe
// bekannt, und die Methode steht auf der Karte, weil eine einzelne Zahl über dreizehn
// Konsolen sonst zum falschen Schluss einlädt.
//
// Und: Nicht jede Plattform hat überhaupt eine Katalogquelle. Eine Karte, die die
// unmessbaren stillschweigend weglässt, meldet eine Vollständigkeit über einen Ausschnitt.
// Deshalb steht „x von y messbar" auf der Karte und nicht in einer Fußnote.
let COVOFFEN=new Set();
async function loadCoverage(){let box=document.getElementById('coverage');
 box.innerHTML='<div class=meta>…</div>';
 let d=await(await fetch('/api/coverage')).json();
 if(!GRUPPEN.length)await loadPlatforms();
 let proSlug={};(d.platforms||[]).forEach(p=>{proSlug[p.slug]=p;});
 let genutzt=new Set();
 let karten=GRUPPEN.map(g=>{
  let plats=g.slugs.map(sl=>proSlug[sl]).filter(Boolean);
  plats.forEach(p=>genutzt.add(p.slug));
  return covGruppe(g.name,plats);}).filter(Boolean);
 // Plattformen, die in keiner Gruppe stehen, gehen sonst lautlos verloren.
 let rest=(d.platforms||[]).filter(p=>!genutzt.has(p.slug));
 if(rest.length)karten.push(covGruppe('—',rest));
 let adm=canDo('manage_settings')?`<button onclick="covRefresh()">${t('cov_refresh')}</button>
   <span id=covmsg class=meta></span>`:'';
 box.innerHTML=`<div class=rowh style="display:flex;align-items:center;gap:10px"><b>📊 ${t('nav_coverage')}</b>
   <span style="margin-left:auto">${adm}</span></div>
  <div class=meta style="margin:6px 0 10px;line-height:1.6">${t('cov_basis').replace('{src}',d.source).replace('{max}',d.max_per_platform)}</div>
  ${karten.join('')}`;
 if(d.building)covPoll();}
function covZeile(p){
 if(p.known==null)return `<div class=job><div><b>${p.name}</b><div class=meta style="font-size:11px">`
   +(p.catalog?t('cov_nosnap'):t('cov_nosource'))+` · ${p.files} ${t('cov_files')}</div></div></div>`;
 let bar=`<div style="background:#2a2f37;border-radius:4px;height:6px;width:120px;overflow:hidden">`
  +`<div style="background:#6c5ce7;height:6px;width:${Math.min(100,p.pct||0)}%"></div></div>`;
 return `<div class=job style="cursor:pointer" onclick="openMissing('${p.slug}','${p.name.replace(/'/g,"")}')">
  <div><b>${p.name}</b><div class=meta style="font-size:11px">${p.owned} ${t('cov_of')} ${p.known}`
  +(p.capped?' +':'')+` · ${p.pct}% · ${t('cov_src')}: ${p.source} · ${t('cov_asof')} ${(p.snapshot||'').slice(0,10)}</div></div>
  <div style="display:flex;align-items:center;gap:10px">${bar}<span class=meta>›</span></div></div>`;}
function covGruppe(name,plats){
 if(!plats.length)return '';
 let messbar=plats.filter(p=>p.known!=null);
 let owned=messbar.reduce((a,p)=>a+(p.owned||0),0);
 let known=messbar.reduce((a,p)=>a+(p.known||0),0);
 let pct=known?Math.round(owned*100/known):null;
 let auf=COVOFFEN.has(name);
 let logo=LOGOS.has(name.toLowerCase())
  ?`<img class=glogo src="/logo/${encodeURIComponent(name.toLowerCase())}" alt="${name}">`:'';
 let bar=pct==null?'':`<div style="background:#2a2f37;border-radius:4px;height:6px;width:120px;overflow:hidden">`
  +`<div style="background:#6c5ce7;height:6px;width:${Math.min(100,pct)}%"></div></div>`;
 let zahl=pct==null?t('cov_nosnap')
  :`${owned} ${t('cov_of')} ${known} · ${pct}% · <span title="${t('cov_method')}">Σ</span>`;
 return `<div class=covgrp>
  <div class="job covhead" onclick="COVOFFEN.${auf?'delete':'add'}('${name.replace(/'/g,"")}');loadCoverage()">
   <div style="display:flex;align-items:center;gap:10px">${logo}<div><b>${name}</b>
    <div class=meta style="font-size:11px">${zahl} · ${t('cov_measurable').replace('{n}',messbar.length).replace('{m}',plats.length)}</div></div></div>
   <div style="display:flex;align-items:center;gap:10px">${bar}<span class=meta>${auf?'▾':'›'}</span></div></div>
  ${auf?`<div class=covkinder>${plats.map(covZeile).join('')}</div>`:''}</div>`;}
async function covRefresh(){let m=document.getElementById('covmsg');m.textContent='…';
 let r=await fetch('/api/coverage/refresh',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
 let d=await r.json();if(!d.ok){m.textContent=d.msg||t('st_error');return;}covPoll();}
async function covPoll(){let m=document.getElementById('covmsg');if(!m)return;
 let st=await(await fetch('/api/coverage/status')).json();
 if(st.running){m.textContent=`${st.current||''} ${st.done}/${st.total}`;setTimeout(covPoll,2000);}
 else{m.textContent=t('done_word');loadCoverage();}}
let _miss={slug:'',name:'',offset:0,q:''};
// ---------- Bibliothek: was ist DA (#293) ----------
// Gegenstueck zur Abdeckung. Dieselbe Gruppierung nach Hersteller wie dort und wie im
// Plattformfilter — eine dritte Liste waere eine dritte Wahrheit.
let LIBOFFEN=new Set(); let _own={slug:'',name:'',offset:0,q:''};
async function loadLibrary(){let box=document.getElementById('library');
 box.innerHTML='<div class=meta>…</div>';
 let d=await(await fetch('/api/library/platforms')).json();
 let karten=(d.vendors||[]).map(g=>libGruppe(g)).join('');
 box.innerHTML=`<div class=rowh style="display:flex;align-items:center;gap:10px"><b>📚 ${t('nav_library')}</b>
   <span class=meta style="margin-left:auto">${(d.total||0).toLocaleString()} ${t('lib_titles')}</span></div>
  <div class=meta style="margin:6px 0 10px;line-height:1.6">${t('lib_hint')}</div>
  ${karten||('<div class=meta>'+t('lib_empty')+'</div>')}`;}
// Herstellernamen kommen fertig aus der API — `Nintendo` heisst in jeder Sprache so.
// Sammelgruppen („Heimcomputer", „Ohne Zuordnung") tun das nicht und liefern deshalb
// einen Schluessel mit dem Praefix `lib_grp_`, der hier uebersetzt wird. (#322)
// Vendor names arrive ready to display; category groups arrive as a `lib_grp_` key.
function libName(v){ return v && v.startsWith('lib_grp_') ? t(v) : v; }
function libGruppe(g){
 let auf=LIBOFFEN.has(g.vendor);
 let anzeige=libName(g.vendor);
 let logo=LOGOS.has(anzeige.toLowerCase())
  ?`<img class=glogo src="/logo/${encodeURIComponent(anzeige.toLowerCase())}" alt="">`:'';
 // WARUM KNOEPFE UND KEINE DIVS: Ein `div` mit `onclick` ist fuer die Tastatur nicht
 // vorhanden und wird von Vorlesern nicht als bedienbar angesagt (#319). `aria-label`
 // fasst Name und Zahl zusammen — eine nackte Zahl hinter einem Namen ist vorgelesen
 // mehrdeutig. axe findet diese Klasse Fehler NICHT; es gibt dafuer keine Regel.
 // A div with onclick is invisible to the keyboard and silent to screen readers; axe has
 // no rule for it, so only a keyboard walk catches it.
 let zeilen=auf?g.platforms.map(p=>`<button class="job libzeile"
   aria-label="${(p.name||'').replace(/"/g,'')} — ${p.owned.toLocaleString()} ${t('lib_titles')}"
   onclick="openOwned('${p.slug}','${(p.name||'').replace(/'/g,'')}')">
   <span><b>${(p.name||'').replace(/</g,'&lt;')}</b></span>
   <span style="display:flex;align-items:center;gap:10px"><span class=meta>${p.owned.toLocaleString()}</span>
   <span class=meta aria-hidden="true">›</span></span></button>`).join(''):'';
 // `aria-expanded` sagt an, ob die Gruppe offen ist; `aria-controls` verbindet den
 // Knopf mit der Liste, die er auf- und zuklappt. Ohne beides hoert ein Vorleser nur
 // einen Knopf mit einem Namen und erfaehrt nie, dass sich darunter etwas geoeffnet hat.
 // aria-expanded announces the state, aria-controls ties the button to the list it opens.
 let lid='libg-'+g.vendor.toLowerCase().replace(/[^a-z0-9]+/g,'-');
 return `<div class=card style="margin-bottom:10px">
  <button class="job covhead libkopf" aria-expanded="${auf}" aria-controls="${lid}"
   onclick="LIBOFFEN.${auf?'delete':'add'}('${g.vendor.replace(/'/g,'')}');loadLibrary()">
   <span style="display:flex;align-items:center;gap:8px">${logo}<b>${anzeige.replace(/</g,'&lt;')}</b></span>
   <span style="display:flex;align-items:center;gap:10px"><span class=meta>${g.owned.toLocaleString()}</span>
   <span class=meta aria-hidden="true">${auf?'▾':'▸'}</span></span></button>
  <div id="${lid}">${zeilen}</div></div>`;}
async function openOwned(slug,name){_own={slug:slug,name:name,offset:0,q:''};renderOwned();}
async function renderOwned(){let m=document.getElementById('modal');m.style.display='block';
 m.innerHTML='<div class=box><div class=meta>…</div></div>';
 let u=`/api/library/${_own.slug}/titles?offset=${_own.offset}&limit=100`+(_own.q?'&q='+encodeURIComponent(_own.q):'');
 let d=await(await fetch(u)).json();
 // Anklickbar: von hier aus fuehrt der Weg zur Suche, wie bei den fehlenden Titeln auch.
 let rows=(d.titles||[]).map(tt=>`<div class=job>
   <span style="flex:1">${String(tt).replace(/</g,'&lt;')}</span>
   <button onclick="missSearch('${String(tt).replace(/'/g,"\\'").replace(/"/g,'&quot;')}')"
    style="background:#2a2f37">${t('cov_search')}</button></div>`).join('')
  ||`<div class=meta>${t('lib_none')}</div>`;
 let pages=`<div class=frow style="gap:8px">
   <button ${_own.offset<=0?'disabled':''} onclick="_own.offset=Math.max(0,_own.offset-100);renderOwned()">‹</button>
   <span class=meta>${d.total?_own.offset+1:0}–${Math.min(d.total,_own.offset+100)} / ${(d.total||0).toLocaleString()}</span>
   <button ${_own.offset+100>=d.total?'disabled':''} onclick="_own.offset+=100;renderOwned()">›</button></div>`;
 m.innerHTML=`<div class=box><button class=x onclick="closeModal()">×</button>
  <h2>${_own.name} — ${t('lib_owned')}</h2>
  <div class=frow style="gap:8px"><input id=ownq value="${(_own.q||'').replace(/"/g,'&quot;')}"
    placeholder="${t('cov_filter')}" style="flex:1">
   <button onclick="_own.q=document.getElementById('ownq').value;_own.offset=0;renderOwned()">${t('cov_filter_do')}</button></div>
  <div style="max-height:340px;overflow:auto;margin-top:8px">${rows}</div>
  ${pages}</div>`;}
async function openMissing(slug,name){_miss={slug:slug,name:name,offset:0,q:''};renderMissing();}
async function renderMissing(){let m=document.getElementById('modal');m.style.display='block';
 m.innerHTML='<div class=box><div class=meta>…</div></div>';
 let u=`/api/coverage/${_miss.slug}/missing?offset=${_miss.offset}&limit=100`+(_miss.q?'&q='+encodeURIComponent(_miss.q):'');
 let d=await(await fetch(u)).json();
 let rows=(d.titles||[]).map((tt,i)=>`<div class=job><label style="display:flex;align-items:center;gap:8px;flex:1">
   <input type=checkbox class=misschk data-title="${tt.replace(/"/g,'&quot;')}"> <span>${tt.replace(/</g,'&lt;')}</span></label>
  <button onclick="missSearch('${tt.replace(/'/g,"\'").replace(/"/g,'&quot;')}')" style="background:#2a2f37">${t('cov_search')}</button></div>`).join('')
  ||`<div class=meta>${t('cov_none')}</div>`;
 let pages=`<div class=frow style="gap:8px">
   <button ${_miss.offset<=0?'disabled':''} onclick="_miss.offset=Math.max(0,_miss.offset-100);renderMissing()">‹</button>
   <span class=meta>${_miss.offset+1}–${Math.min(d.total,_miss.offset+100)} / ${d.total}</span>
   <button ${_miss.offset+100>=d.total?'disabled':''} onclick="_miss.offset+=100;renderMissing()">›</button></div>`;
 m.innerHTML=`<div class=box><button class=x onclick="closeModal()">×</button>
  <h2>${_miss.name} — ${t('cov_missing')}</h2>
  <div class=meta style="margin-bottom:8px">${t('cov_src')}: ${d.source||'—'} · ${t('cov_asof')} ${(d.snapshot||'').slice(0,10)}</div>
  <div class=frow style="gap:8px"><input id=missq value="${(_miss.q||'').replace(/"/g,'&quot;')}" placeholder="${t('cov_filter')}" style="flex:1">
   <button onclick="_miss.q=document.getElementById('missq').value;_miss.offset=0;renderMissing()">${t('cov_filter_do')}</button></div>
  <div style="max-height:340px;overflow:auto;margin-top:8px">${rows}</div>
  ${pages}
  <div class=frow style="justify-content:flex-end;gap:8px"><span id=missmsg class=meta></span>
   <button onclick="missWish()">${t('cov_wish_sel')}</button></div></div>`;}
function missSearch(title){closeModal();document.getElementById('q').value=title;show('s');search();}
async function missWish(){let sel=[...document.querySelectorAll('.misschk')].filter(c=>c.checked)
  .map(c=>({title:c.dataset.title,platform:_miss.slug}));
 let msg=document.getElementById('missmsg');
 if(!sel.length){msg.textContent=t('wl_imp_none');return;}
 let d=await(await fetch('/api/wishlist/import',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({confirm:true,entries:sel})})).json();
 msg.textContent=t('wl_imp_done').replace('{a}',d.added||0).replace('{s}',d.skipped||0);}
let msgWith='';
async function loadMessages(){let box=document.getElementById('messages');let d=await(await fetch('/api/messages')).json();
 let me=d.me,users=d.users||[];if(!msgWith&&users.length)msgWith=users[0];
 let unreadBy={};(d.messages||[]).forEach(m=>{if(m.to==me&&!m.read)unreadBy[m.from]=(unreadBy[m.from]||0)+1;});
 let opts=users.map(u=>`<option value="${u}" ${u==msgWith?'selected':''}>${u.replace(/</g,'&lt;')}${unreadBy[u]?' ('+unreadBy[u]+')':''}</option>`).join('');
 let thread=(d.messages||[]).filter(m=>(m.from==msgWith&&m.to==me)||(m.from==me&&m.to==msgWith))
   .map(m=>`<div class=cmt style="max-width:80%;margin-left:${m.from==me?'auto':'0'}"><span class="cu${m.from==me?' staff':''}">${m.from.replace(/</g,'&lt;')}</span> <span class=meta style="font-size:10px">${new Date(m.ts*1000).toLocaleString()}</span><div>${m.body.replace(/</g,'&lt;')}</div></div>`).join('');
 box.innerHTML=`<div style="padding:18px;max-width:680px"><h3 style="text-transform:uppercase;color:#8b929e;font-size:12px">✉ ${t('nav_messages')}</h3>`+
  (users.length?`<div class=frow><label for=msgsel style="min-width:auto">${t('msg_to')}</label><select id=msgsel onchange="msgWith=this.value;loadMessages()">${opts}</select></div>
   <div class=cmts id=msgthread style="max-height:50vh;overflow:auto">${thread||('<div class=meta>'+t('msg_none')+'</div>')}</div>
   <div class=frow><textarea id=msgbody placeholder="${t('msg_ph')}" style="flex:1;min-height:60px;background:#0b0d10;border:1px solid #2c323b;color:#e6e8ec;padding:8px;border-radius:6px" onkeydown="if(event.key=='Enter'&&event.ctrlKey)sendMsg()"></textarea></div>
   <div class=frow><button onclick="sendMsg()">${t('msg_send')}</button><span class=meta>${t('msg_hint')}</span></div>`:`<div class=meta>${t('msg_nousers')}</div>`)+`</div>`;
 if(msgWith&&unreadBy[msgWith]){await fetch('/api/messages/read',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({from:msgWith})});updateMsgBadge();}
 let mt=document.getElementById('msgthread');if(mt)mt.scrollTop=mt.scrollHeight;}
async function sendMsg(){let b=document.getElementById('msgbody');let body=(b.value||'').trim();if(!body||!msgWith)return;
 let r=await(await fetch('/api/messages',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({to:msgWith,body})})).json();
 if(r.ok){b.value='';loadMessages();}}
// Zähler an „Anfragen" (#198): steigt, solange etwas unerledigt ist, und geht auf Null,
// wenn nichts mehr offen ist — dann verschwindet er GANZ. Eine `0` wäre eine Zahl, die
// man liest und wieder vergisst; kein Abzeichen ist die klarere Aussage.
//
// EIGENE Aufträge, auch für Verwalter (die zweite offene Frage im Issue). Zählte er für
// einen Admin alle, wäre er praktisch nie null und würde damit aufhören, etwas zu
// bedeuten. Wer alles sehen will, hat auf der Seite den Nutzerfilter.
async function updateJobBadge(){
 try{
  let d=await(await fetch('/api/jobs')).json();
  let el=document.getElementById('jobbadge');if(!el)return;
  let meine=d.filter(o=>!window.ME||!o.user||o.user===window.ME);
  let offen=meine.filter(jobOffen);
  let fehler=offen.some(o=>jobGruppe(o.state)==='fehler');
  el.textContent=offen.length?' '+offen.length+' ':'';
  el.style.cssText=offen.length
   ?`background:${fehler?'#c0392b':'#2a6f4b'};color:#fff;border-radius:10px;padding:0 6px;font-size:11px;margin-left:6px`:'';
  el.title=offen.length?(fehler?t('flt_failed'):t('flt_active')):'';
 }catch(e){}}
async function updateMsgBadge(){try{let d=await(await fetch('/api/messages')).json();let el=document.getElementById('msgbadge');if(!el)return;
 el.textContent=d.unread?' '+d.unread+' ':'';el.style.cssText=d.unread?'background:#c0392b;color:#fff;border-radius:10px;padding:0 6px;font-size:11px;margin-left:6px':'';}catch(e){}}
async function loadIssues(pref){let box=document.getElementById('issues');
 let items=await(await fetch('/api/issues')).json();
 let types=['broken','wrong_region','wrong_platform','other'];
 box.innerHTML=`<div style="padding:18px;max-width:640px">
  <h3 style="text-transform:uppercase;color:#8b929e;font-size:12px">${t('report_issue')}</h3>
  <div class=frow><input id=itit placeholder="Titel / title" value="${((pref&&pref.title)||'').replace(/"/g,'&quot;')}"></div>
  <div class=frow><input id=iplat placeholder="Plattform" style="flex:0 0 140px" value="${((pref&&pref.platform)||'').replace(/"/g,'&quot;')}"><select id=ityp aria-label="Art / type">${types.map(x=>'<option>'+x+'</option>').join('')}</select></div>
  <div class=frow><textarea id=imsg placeholder="${t('issue_msg')}" style="flex:1;min-height:60px;background:#0b0d10;border:1px solid #2c323b;color:#e6e8ec;padding:8px;border-radius:6px"></textarea></div>
  <div class=frow><button onclick="submitIssue()">${t('submit')}</button><span id=imm class=meta></span></div>
  <h3 style="text-transform:uppercase;color:#8b929e;font-size:12px;margin-top:20px">${t('issues')}</h3><div id=ilist></div></div>`;
 renderIssues(items);}
function renderIssues(items){let d=document.getElementById('ilist');d.innerHTML=items.length?'':'<div class=meta>—</div>';
 items.forEach(i=>{let e=document.createElement('div');e.className='job';e.style.flexDirection='column';e.style.alignItems='stretch';
  let st=i.status=='closed'?t('st_closed'):t('st_open');
  let right=(canDo('manage_issues')&&i.status!='closed')?`<button onclick="closeIssue('${i.id}')" style="background:#1e5e3a;border:none;color:#fff;padding:5px 10px;border-radius:6px;cursor:pointer">${t('close_btn')}</button>`:`<span class="st ${i.status=='closed'?'done':''}">${st}</span>`;
  let cs=(i.comments||[]).map(c=>`<div class=cmt><span class="cu${c.staff?' staff':''}">${(''+(c.user||'')).replace(/</g,'&lt;')}${c.staff?' 🛠':''}</span> <span class=meta style="font-size:10px">${c.ts||''}</span><div>${(''+(c.text||'')).replace(/</g,'&lt;')}</div></div>`).join('');
  e.innerHTML=`<div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start"><div><div>${(''+(i.title||'')).replace(/</g,'&lt;')} <span class=meta>(${i.type})</span></div><div class=meta style="font-size:11px">👤 ${(''+(i.user||'')).replace(/</g,'&lt;')} · ${i.platform||''} · ${i.ts||''} · ${(''+(i.message||'')).replace(/</g,'&lt;').slice(0,90)}</div></div><div>${right}</div></div>
   <div class=cmts>${cs}</div>
   <div class=frow style="margin-top:6px"><input id="ic_${i.id}" placeholder="${t('comment_ph')}" style="flex:1" onkeydown="if(event.key=='Enter')addComment('${i.id}')"><button onclick="addComment('${i.id}')">${t('comment_send')}</button></div>`;
  d.appendChild(e);});}
async function addComment(id){let inp=document.getElementById('ic_'+id);let txt=inp.value.trim();if(!txt)return;
 let r=await(await fetch('/api/issues/'+id+'/comment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:txt})})).json();
 if(r.ok)loadIssues();}
async function submitIssue(){let d={title:document.getElementById('itit').value,platform:document.getElementById('iplat').value,type:document.getElementById('ityp').value,message:document.getElementById('imsg').value};
 if(!d.title.trim()){document.getElementById('imm').textContent='Titel fehlt / title missing';return;}
 let r=await(await fetch('/api/issues',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 if(r.ok)loadIssues();}
async function closeIssue(id){await fetch('/api/issues/'+id+'/close',{method:'POST'});loadIssues();}
function reportFromDetail(){let it=window._detit;if(!it)return;closeModal();window._ipref={title:it.title,platform:it.platform_slug};show('issues');}
function sz(b){if(!b)return'';let u=['B','KB','MB','GB','TB'],i=0;while(b>=1024&&i<4){b/=1024;i++}return b.toFixed(1)+' '+u[i];}
// Der Zustand gehoert AUF das Cover (#205). Vorher stand er als 12px-Zeile unten im
// Aktionsfeld — also dort, wohin das Auge erst geht, wenn es sich schon entschieden hat,
// und in der kleinsten Schrift der Seite. Das Abzeichen liegt oben rechts wie `.have2`
// und wird gesehen, bevor der Titel gelesen ist.
// ZWEI Zustaende, nicht einer: „vorhanden" und „angefragt" sind verschieden, und beide
// interessieren VOR dem Klick. Und nie nur Farbe — gruen auf dunklem Cover sagt einem
// rot-gruen-blinden Menschen nichts, deshalb traegt das SYMBOL die Bedeutung.
function kartenZustand(it){
 // Die Textbausteine tragen selbst schon ein Symbol („✓ in Bibliothek", „✓ angefragt") —
 // es wird hier entfernt und durch ein UNTERSCHEIDENDES ersetzt. Sonst stünde zweimal
 // dasselbe Zeichen da, und die beiden Zustände wären wieder nur an der Farbe zu trennen.
 let ohne=x=>x.replace(/^[✓⏳⬇]\s*/,'');
 if(it.in_library)return{cls:'da',zeichen:'✓',text:ohne(t('in_library'))};
 if(it.requested)return{cls:'req',zeichen:'⏳',text:ohne(t('requested'))};
 return null;}
function renderCard(it){let c=document.createElement('div');c.className='card';
 let cov=it.cover?`background-image:url('${it.cover}')`:'';
 let src=it.source=='usenet'?'📡 Usenet':'🗄 Archive';
 let settag=it.is_set?' · 📦 '+t('collection'):'';
 // Zugangsbeschraenkt heisst: Der Download braucht ein Archive.org-Konto und scheitert
 // sonst mit HTTP 401 — nach dem Klick, bei "Mario Kart 8" nach 5,5 GB vergeblichem
 // Warten. Der Treffer bleibt sichtbar, sagt es aber VORHER. (#382)
 let gesperrt=it.restricted?' · 🔒 '+t('needs_ia_login'):'';
 let z=kartenZustand(it);
 // Anzeigename statt rohem Slug (#211): die Karte sagte `ngc` statt „GameCube". Die
 // Namen kommen aus /api/platforms, dieselbe Quelle wie die Filterleiste — kein zweiter
 // Datenbestand, der auseinanderlaufen kann. `?` bleibt `?`, das ist ein echter Fall.
 let plat=plattformMarke(it.platform_slug);
 c.innerHTML=`<div class=cover style="${cov}"><span class=badge>${plat}</span><span class=src>${src}</span>`+
  (z?`<span class="zust ${z.cls}" title="${z.text}">${z.zeichen} ${z.text}</span>`:'')+`</div>
  <div class=body><div class=t>${FAVS.has(norm(it.title||''))?'<span class=favmark title="'+t('favourite')+'">♥</span> ':''}${it.title.replace(/</g,'&lt;')}</div><div class=meta>${sz(it.size)}${settag}${gesperrt}</div><div class=act></div></div>`;
 c.querySelector('.cover').onclick=()=>openDetail(it);
 let tt=c.querySelector('.t');tt.style.cursor='pointer';tt.onclick=()=>openDetail(it);
 let act=c.querySelector('.act');
 // Das Aktionsfeld sagt, was man TUN kann — es wiederholt nicht den Zustand, der jetzt
 // oben steht. Vorhanden: zu den Details (dort liegen Spielen und Streamen). Angefragt:
 // ein abgeschalteter Knopf, damit niemand ein zweites Mal anfragt.
 if(it.in_library){let b=document.createElement('button');b.className='dl zw';
  b.textContent=t('details');b.onclick=()=>openDetail(it);act.appendChild(b);}
 else if(it.requested){let b=document.createElement('button');b.className='dl zw';
  b.textContent=t('requested');b.disabled=true;act.appendChild(b);}
 else{let b=document.createElement('button');b.className='dl';b.textContent=t('download');b.onclick=()=>dl(b,it);act.appendChild(b);}
 if(!it.cover)fetch('/api/cover?title='+encodeURIComponent(it.title)).then(r=>r.json()).then(d=>{
  if(d.cover){it.cover=d.cover;c.querySelector('.cover').style.backgroundImage="url('"+d.cover+"')";}});
 return c;}

let RAONLY=false;
function toggleRA(){RAONLY=!RAONLY;let b=document.getElementById('tRA');
 b.classList.toggle('on',RAONLY);b.textContent=RAONLY?'🏆 '+t('ra_only'):'🏆';
 if(document.getElementById('q').value.trim())search();}
async function search(){let q=document.getElementById('q').value.trim();if(!q){loadDiscover();return;}
 let hint=document.getElementById('hint');hint.style.display='';hint.textContent=t('searching');
 let r=await fetch('/api/search?q='+encodeURIComponent(q)+'&platforms='+[...SELP].join(',')+(RAONLY?'&achievements=1':''));let d=await r.json();
 window.LASTRES=d;let g=document.getElementById('grid');g.className='';g.innerHTML='';
 if(!d.length){document.getElementById('hint').textContent=t('no_results');return;}
 let games={};d.forEach(x=>{if(!x.in_library){let k=x.gkey||x.title;if(!games[k])games[k]=1;}});
 let n=Object.keys(games).length;
 hint.innerHTML=(d.length+' '+t('results')).replace(/</g,'&lt;');
 if(n>1&&canDo('request')){let b=document.createElement('button');b.id='bulkbtn';
  b.style.cssText='margin-left:12px;background:#2a2f37;border:none;color:#e6e8ec;padding:5px 12px;border-radius:6px;cursor:pointer;font-size:12px';
  b.textContent='⬇ '+t('req_all')+' ('+n+')';b.onclick=bulkRequest;hint.appendChild(b);}
 d.forEach(it=>g.appendChild(renderCard(it)));}
async function bulkRequest(){let b=document.getElementById('bulkbtn');if(b)b.disabled=true;
 let seen={},todo=[];(window.LASTRES||[]).forEach(it=>{if(it.in_library)return;let k=it.gkey||it.title;if(seen[k])return;seen[k]=1;todo.push(it);});
 let ok=0;for(let it of todo){try{let r=await(await fetch('/api/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.assign({},it,{for_user:window.reqFor||''}))})).json();if(r.ok)ok++;}catch(e){}
  if(b)b.textContent='⬇ '+ok+'/'+todo.length;}
 if(b)b.textContent='✓ '+ok+'/'+todo.length;}
async function dl(btn,it){btn.disabled=true;btn.textContent='…';
 let payload=Object.assign({},it,{for_user:window.reqFor||''});
 let r=await fetch('/api/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
 let d=await r.json();btn.textContent=d.ok?t('requested'):(d.msg||t('st_error'));}
// --- Detail-Ansicht (Seerr-Detailseite) ---
// `ausRoute` unterscheidet den Klick vom Wiederherstellen: beim Klick kommt ein neuer
// Verlaufseintrag dazu (damit Zurück das Fenster schliesst), beim Wiederherstellen aus
// der Adresse nicht — sonst entstünde bei jedem Zurück ein neuer Eintrag. (#194)
async function openDetail(it,ausRoute){let m=document.getElementById('modal');m.style.display='block';window._detit=it;window.reqFor='';
 if(!ausRoute)routeSetzen(cur,it);
 let vars=(window.LASTRES||[]).filter(x=>x.gkey&&x.gkey===it.gkey);
 m.innerHTML=`<div class=box><button class=x onclick="closeModal()">×</button>
  <div class=top><div class=mc style="${it.cover?`background-image:url('${it.cover}')`:''}"></div>
   <div><h2>${it.title.replace(/</g,'&lt;')}</h2>
    <div class=meta>${SLUGNAME[it.platform_slug]||it.platform_slug||'?'} · ${it.source=='usenet'?'📡 Usenet':'🗄 Archive'} · ${sz(it.size)}${it.is_set?' · 📦 Sammlung':''}</div>
    <div class=meta2 id=mrich></div>
    <button onclick="reportFromDetail()" style="margin-top:8px;background:#2a2f37;border:none;color:#fff;padding:6px 10px;border-radius:6px;cursor:pointer;font-size:12px">🐞 ${t('report_issue')}</button>
    <button id=wlbtn onclick="addWishlist(this)" style="margin-top:8px;margin-left:6px;background:#2a2f37;border:none;color:#fff;padding:6px 10px;border-radius:6px;cursor:pointer;font-size:12px">${t('add_wishlist')}</button>
    <button id=favbtn class="favbtn${FAVS.has(norm(it.title||''))?' on':''}" onclick="toggleFav(window._detit,this)">${(FAVS.has(norm(it.title||''))?'♥ ':'♡ ')+t('favourite')}</button>
    <div class=desc id=mdesc>…</div></div></div>
  <div class=sec id=mrate></div>
  <div class=sec id=mshots style="display:none"><h3>${t('screenshots')}</h3><div class=shots id=mshotsw></div></div>
  <div id=mra style="display:none;margin:6px 0"></div>
  <div id=mplay style="display:none;margin:6px 0"></div>
  <div id=mstream style="display:none;margin:6px 0"></div>
  <div class=sec><h3>${t('versions')} (${vars.length})</h3><div id=reqforbar></div><div id=mvar></div></div>
  <div class=sec id=mfiles></div>
  <div class=sec id=mser style="display:none"><h3 id=mserh>${t('series')}</h3><div class=chips id=mserw></div></div>
  <div class=sec id=msim style="display:none"><h3>${t('similar')}</h3><div class=chips id=msimw></div></div></div>`;
 let mv=document.getElementById('mvar');
 // Kandidaten nach FASSUNG gruppieren statt rohe Release-Namen aufzulisten. (#77)
 // Bei genau einem Kandidaten aendert sich nichts — der haeufige Fall darf keinen Klick kosten.
 if(vars.length>1){
  let groups={};vars.forEach(v=>{let k=v.variant_label||'';(groups[k]=groups[k]||[]).push(v);});
  let keys=Object.keys(groups);
  keys.forEach((k,gi)=>{
   let h=document.createElement('div');h.className='meta';
   h.style.cssText='margin:8px 0 2px;font-size:11px;letter-spacing:.03em';
   h.textContent=(k||t('var_unspec'))+(gi===0?' · '+t('var_preferred'):'');
   mv.appendChild(h);
   groups[k].forEach(v=>mv.appendChild(varRow(v)));});
 }else{vars.forEach(v=>mv.appendChild(varRow(v)));}
 // `/api/users` liefert eine LISTE von Objekten, keinen Namen-Dictionary. Object.keys()
 // gab darauf die Indizes zurück — die Auswahl bot „0" und „1" an. Der interne Speicher
 // ist ein Dictionary, der Endpunkt macht daraus eine Liste; diese Aufrufstelle war gegen
 // den internen Aufbau geschrieben. (#209)
 if(canDo('manage_requests')){try{let us=await(await fetch('/api/users')).json();
   let names=(Array.isArray(us)?us:[]).map(u=>u&&u.username).filter(Boolean).sort();
   if(names.length){let bar=document.getElementById('reqforbar');
    bar.innerHTML=`<div class=frow style="margin-bottom:8px"><label for=reqforsel style="min-width:auto;color:#8b929e;font-size:12px">${t('req_for')}</label><select id=reqforsel onchange="window.reqFor=this.value"><option value="">${t('req_self')}</option>${names.map(u=>`<option value="${u}">${u.replace(/</g,'&lt;')}</option>`).join('')}</select></div>`;}}catch(e){}}
 let r=await fetch('/api/detail?source='+encodeURIComponent(it.source)+'&ref='+encodeURIComponent(it.ref||'')+'&title='+encodeURIComponent(it.title)+'&platform='+encodeURIComponent(it.platform_slug||''));
 let d=await r.json();
 window._detname=d.name||'';
 // RetroAchievements: nur wenn ein Set zugeordnet ist. Kein Set / kein Dienst -> gar nichts. (#79)
 loadPlay(it);loadStream(it);loadTitleMeta(it);
 let rabox=document.getElementById('mra');
 if(rabox){if(d.achievements){let a=d.achievements;
   let pr=a.progress?` · <b>${a.progress.earned}/${a.progress.total||a.achievements}</b> ${t('ra_earned')}`
        +(a.progress.completion?` (${a.progress.completion})`:''):'';
   rabox.style.display='';
   rabox.innerHTML=`<span class=badge>🏆 ${a.achievements} ${t('ra_achievements')}</span> `
    +`<span class=meta>${a.points} ${t('ra_points')}${pr} · `
    +`<a href="${a.url}" target=_blank rel=noopener style="color:#5b8cff">RetroAchievements</a></span>`;}
  else rabox.style.display='none';}
 document.getElementById('mdesc').textContent=d.description||t('no_desc');
 let rb=[];
 if(d.rating)rb.push(`<span class=badge>★ ${d.rating}</span>`);
 if(d.year)rb.push(`<span class=badge>${d.year}</span>`);
 if(d.developer)rb.push(`<span class=badge>${d.developer.replace(/</g,'&lt;')}</span>`);
 (d.genres||[]).slice(0,4).forEach(g=>rb.push(`<span class="badge g">${g.replace(/</g,'&lt;')}</span>`));
 document.getElementById('mrich').innerHTML=rb.join(' ');
 if(d.screenshots&&d.screenshots.length){document.getElementById('mshots').style.display='';
   document.getElementById('mshotsw').innerHTML=d.screenshots.map(s=>`<img src="${s}" loading=lazy>`).join('');}
 if(d.similar&&d.similar.length){document.getElementById('msim').style.display='';
   document.getElementById('msimw').innerHTML=d.similar.map(n=>`<button class=chip onclick="simSearch(this.dataset.n)" data-n="${n.replace(/"/g,'&quot;')}">${n.replace(/</g,'&lt;')}</button>`).join('');}
 if(d.series&&d.series_games&&d.series_games.length){document.getElementById('mser').style.display='';
   document.getElementById('mserh').textContent=t('series')+': '+d.series;
   document.getElementById('mserw').innerHTML=d.series_games.map(n=>`<button class=chip onclick="simSearch(this.dataset.n)" data-n="${n.replace(/"/g,'&quot;')}">${n.replace(/</g,'&lt;')}</button>`).join('');}
 if(d.files&&d.files.length)document.getElementById('mfiles').innerHTML='<h3>'+t('files')+'</h3><div class=flist>'+
   d.files.map(f=>`<div>${f.name.replace(/</g,'&lt;')} — ${sz(f.size)}</div>`).join('')+'</div>';}
function simSearch(n){closeModal();document.getElementById('q').value=n;show('s');search();}
async function addWishlist(btn){btn.disabled=true;let it=window._detit||{};
 let r=await(await fetch('/api/wishlist',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:window._detname||it.title||'',platform:it.platform_slug||''})})).json();
 btn.textContent=r.ok?t('wl_added'):(r.msg||t('st_error'));}
function varRow(v){let row=document.createElement('div');row.className='row';
 let s=document.createElement('span');
 s.textContent=`${v.source=='usenet'?'📡':'🗄'} ${sz(v.size)} · ${SLUGNAME[v.platform_slug]||v.platform_slug} · ${v.title.slice(0,48)}`;
 row.appendChild(s);let b=document.createElement('button');
 if(v.in_library){b.textContent='✓ vorhanden';b.disabled=true;}else{b.textContent='⬇ Download';b.onclick=()=>dl(b,v);}
 row.appendChild(b);return row;}
// --- Fassungswahl: Voreinstellungen (Profil + Instanz) (#77) ---
// Regionsreihenfolge als sortierbare Liste; leer = Standard. Die Reihenfolge IST die Praeferenz.
function varPrefFields(pfx,v,regions){
 let order=(v.regions||[]);let rest=(regions||[]).filter(r=>order.indexOf(r)<0);
 let opts=(sel)=>['',...order,...rest].filter((x,i,a)=>a.indexOf(x)===i)
   .map(r=>`<option value="${r}" ${r===sel?'selected':''}>${r||'—'}</option>`).join('');
 let sels=[0,1,2,3].map(i=>`<select id="${pfx}vr${i}" style="background:#1a1d23;color:#e6e8ec;border:1px solid #2a2f37;border-radius:6px;padding:4px 6px;margin-right:4px">${opts(order[i]||'')}</select>`).join('');
 let langs=['','en','de','fr','es','it','ja','pt','nl','sv','pl','ru'];
 return `<div class=meta style="font-size:11px;margin-bottom:4px">${t('var_region_order')}</div>${sels}
  <div class=meta style="font-size:11px;margin:6px 0 4px">${t('var_lang')}</div>
  <select id="${pfx}vl" style="background:#1a1d23;color:#e6e8ec;border:1px solid #2a2f37;border-radius:6px;padding:4px 6px">
   ${langs.map(l=>`<option value="${l}" ${l===(v.lang||'')?'selected':''}>${l?l.toUpperCase():'—'}</option>`).join('')}</select>
  <label style="display:block;margin-top:6px;font-size:12px;color:#8b929e">
   <input type=checkbox id="${pfx}vp" ${v.prerelease?'checked':''}> ${t('var_prerelease')}</label>`;}
function readVarPrefs(pfx){let regions=[];
 [0,1,2,3].forEach(i=>{let e=document.getElementById(pfx+'vr'+i);
  if(e&&e.value&&regions.indexOf(e.value)<0)regions.push(e.value);});
 return {regions:regions,lang:(document.getElementById(pfx+'vl')||{}).value||'',
         prerelease:!!(document.getElementById(pfx+'vp')||{}).checked};}
// --- Play im Browser (#69): Verweis in RomMs eingebauten EmulatorJS-Spieler ---
// Der Knopf erscheint NUR, wenn es einen Kern gibt UND die Datei in RomM liegt.
// Sonst steht dort der Grund — ein Knopf, der nichts tut, ist schlimmer als keiner.
async function loadPlay(it){let box=document.getElementById('mplay');if(!box)return;
 if(!canDo('request')){box.style.display='none';return;}
 let d={};try{d=await(await fetch('/api/play?title='+encodeURIComponent(it.title)
   +'&platform='+encodeURIComponent(it.platform_slug||''))).json();}catch(e){box.style.display='none';return;}
 box.style.display='';
 if(d.playable){
  let notes=[];
  if(d.needs_bios)notes.push(t('play_bios'));
  if(d.caveat==='romset')notes.push(t('play_romset'));
  box.innerHTML=`<a href="${d.url}" target=_blank rel=noopener class=badge
    style="background:#1e5e3a;color:#fff;text-decoration:none;padding:6px 12px;border-radius:8px">▶ ${t('play')}</a>`
   +(notes.length?` <span class=meta style="color:#d29922">${notes.join(' · ')}</span>`:'');
 }else{
  const why={no_romm:'play_no_romm',no_core:'play_no_core',not_in_library:'play_not_in_lib',
             too_large:'play_too_large',no_title:'play_no_title'};
  let msg=t(why[d.reason]||'play_no_core');
  if(d.reason==='too_large')msg=msg.replace('{mb}',Math.round((d.limit||0)/1048576));
  box.innerHTML=`<span class=meta>▶ ${msg}</span>`;}}
// Jeder Grund, den stream_info liefern kann, braucht hier einen Eintrag. Die Lücke, die
// #175 auslöste, entstand genau dadurch, dass ein neuer Code im Server keinen Text in der
// Oberfläche bekam und stumm im allgemeinen Satz verschwand — ein Test hält beide Seiten
// jetzt in Schritt. Codes ohne eigenen Text zeigen bewusst `stream_no`.
const STREAM_GRUND={no_host:'stream_no',use_play:'stream_no',not_supported:'stream_no',
 not_in_library:'stream_not_in_lib',ambiguous_platform:'stream_ambiguous',
 busy:'stream_busy',
 // 3DS: die Absage kommt jetzt VOR der Platzvergabe, mit eigenem Text je Grund —
 // „geht nicht" allein laesst den Nutzer raten, ob es an ihm, am Titel oder am
 // Dienst liegt. (#299)
 encrypted:'stream_encrypted',cia_not_bootable:'stream_cia',
 cia_update:'stream_cia_update',cia_dlc:'stream_cia_dlc',cia_unreadable:'stream_cia_broken',
 // Switch (#427) und Wii U (#512). Die nsp_*-Texte lagen seit #427 in allen fuenf
 // Sprachen bereit und waren UNERREICHBAR — sie fehlten nur hier, und der Test, der
 // das haette sehen sollen, schaute an ihnen vorbei (#513).
 nsp_update:'stream_nsp_update',nsp_dlc:'stream_nsp_dlc',
 wiiu_update:'stream_wiiu_update',wiiu_dlc:'stream_wiiu_dlc',
 wiiu_system:'stream_wiiu_system',
 '':'stream_no'};
// --- Stream (#71): Plattformen OHNE Browser-Kern laufen auf dem Streaming-Host ---
// Einzelplatz: eine Sitzung gleichzeitig. Das muss dastehen, nicht beim zweiten Versuch knallen.
async function loadStream(it){let box=document.getElementById('mstream');if(!box)return;
 if(!canDo('request')){box.style.display='none';return;}
 let d={};try{d=await(await fetch('/api/stream?title='+encodeURIComponent(it.title)
   +'&platform='+encodeURIComponent(it.platform_slug||''))).json();}catch(e){box.style.display='none';return;}
 // Gibt es einen Browser-Kern, ist Play die bessere Wahl — dann gar keinen Stream-Knopf zeigen.
 if(d.reason==='use_play'||d.reason==='not_supported'||d.reason==='no_host'){box.style.display='none';return;}
 box.style.display='';
 if(d.streamable){
  box.innerHTML=`<button onclick="startStream(this,'${(it.title||'').replace(/'/g,"\\'")}','${it.platform_slug||''}')"
    style="background:#2a4d8f;border:none;color:#fff;padding:6px 12px;border-radius:8px;cursor:pointer">📺 ${t('stream')}</button>
   <span class=meta style="margin-left:8px">${(d.seats||1)>1
     ? t('stream_seats').replace('{f}',(d.seats_free==null?d.seats:d.seats_free)).replace('{n}',d.seats)
     : t('stream_single')}</span>`;
 }else if(d.reason==='busy'){
  box.innerHTML=`<span class=meta style="color:#d29922">📺 ${t('stream_busy').replace('{u}',(d.busy_user||'?')).replace('{g}',(d.busy_with||'?'))}</span>
   <button onclick="stopStream()" style="margin-left:8px;background:#2a2f37;border:none;color:#e6e8ec;padding:4px 10px;border-radius:6px;cursor:pointer">${t('stream_stop')}</button>`;
 }else if(d.reason==='ambiguous_platform'&&(d.candidates||[]).length){
  // Der einzige Grund, den der Bedienende auflösen KANN — also fragen statt absagen.
  // Der Resolver kennt die Kandidaten ohnehin; eine Sackgasse wäre hier Verschwendung. (#175)
  box.innerHTML=`<span class=meta>📺 ${t('stream_ambiguous')}</span> `
   +d.candidates.map(p=>`<button onclick="startStream(this,'${(it.title||'').replace(/'/g,"\\'")}','${p}')"
      style="margin-left:6px;background:#2a4d8f;border:none;color:#fff;padding:5px 11px;border-radius:8px;cursor:pointer">📺 ${plattformMarke(p)}</button>`).join('');
 }else{
  box.innerHTML=`<span class=meta>📺 ${t(STREAM_GRUND[d.reason]||'stream_no')}</span>`;}}
async function startStream(btn,title,plat){btn.disabled=true;btn.textContent='…';
 let r=await fetch('/api/stream/start',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({title:title,platform:plat})});
 let d=await r.json();
 if(r.status===409){btn.disabled=false;
  btn.textContent=t('stream_busy').replace('{u}',d.busy_user||'?').replace('{g}',d.busy_with||'?');return;}
 if(!d.streamable){btn.disabled=false;btn.textContent=t('stream_no');return;}
 // Ohne Start-Dienst kann Romseerr den Titel nicht selbst starten — dann ehrlich sagen,
 // dass der Nutzer ihn im Streaming-Desktop oeffnen muss.
 // Scheitert der Start, darf das nicht wie der normale Fall ohne Start-Dienst
 // aussehen — sonst sucht niemand den Grund. Der Grund kommt vom Start-Dienst.
 btn.textContent=d.launched?t('stream_running')
   :(d.launch_error?t('stream_failed'):t('stream_manual'));
 if(d.launch_error||d.launch_reason){let s=document.createElement('div');s.className='meta';
  s.style.cssText='margin-top:6px;color:#d29922;font-size:11px';
  // Ein falsches Token ist etwas anderes als ein toter Host — beides sah gleich aus, und
  // der Betreiber suchte am falschen Ende. (#177)
  s.textContent=d.launch_reason==='bad_token'?t('stream_badtoken'):d.launch_error;
  btn.parentNode.appendChild(s);}
 window.open(d.url,'_blank','noopener');}
async function stopStream(){await fetch('/api/stream/stop',{method:'POST'});closeModal();}
// Ohne Argument ist Schliessen eine Navigation: zurueck zur Ansicht, aus der das Fenster
// geoeffnet wurde. `ausRoute` schliesst nur die Anzeige — dann hat der Verlauf sich
// bereits bewegt und ein weiterer history.back() wuerde aus der App hinausfuehren. (#194)
function closeModal(ausRoute){
 document.getElementById('modal').style.display='none';
 // Fokus dorthin zurück, wo er herkam. Das ist der Teil eines Focus-Traps, der am
 // häufigsten fehlt — ohne ihn landet ein Tastaturnutzer nach jedem Schließen am
 // Seitenanfang und muss sich erneut durch die Seite hangeln. (#258)
 if(_fokusVorDialog&&document.contains(_fokusVorDialog)){try{_fokusVorDialog.focus();}catch(e){}}
 _fokusVorDialog=null;
 if(ausRoute)return;
 if(!routeParse(location.hash).detail)return;
 // Zurueck nur, wenn wir den Eintrag selbst angelegt haben. Wurde der Titel direkt ueber
 // seine Adresse geoeffnet, gibt es nichts Eigenes davor — dann die Adresse ERSETZEN,
 // sonst schliesst das Fenster die Anwendung. (#226)
 if(EIGENE_SCHRITTE>0)history.back();
 else routeSetzen(cur,null,true);
}
// --- Wunschlisten-Import: Vorschau ZUERST, geschrieben wird erst nach Bestaetigung (#80) ---
const WLST={matched:['#3fb950','wl_s_matched'],ambiguous:['#d29922','wl_s_ambiguous'],
 not_found:['#f85149','wl_s_notfound'],duplicate:['#8b929e','wl_s_duplicate'],
 in_library:['#8b929e','wl_s_inlib'],unverified:['#58a6ff','wl_s_unverified']};
function openWlImport(){let m=document.getElementById('modal');m.style.display='block';
 m.innerHTML=`<div class=box><button class=x onclick="closeModal()">×</button>
  <h2>⭐ ${t('wl_import')}</h2>
  <div class=meta style="line-height:1.6;margin-bottom:10px">${t('wl_imp_hint')}
   · <a href="/api/wishlist/example.csv" download style="color:#5b8cff">${t('wl_imp_example')}</a></div>
  <textarea id=wlta placeholder="${t('wl_imp_ph')}" style="width:100%;min-height:150px;background:#0b0d10;border:1px solid #2c323b;color:#e6e8ec;padding:8px;border-radius:8px;font-family:ui-monospace,monospace;font-size:12px"></textarea>
  <div class=frow style="gap:8px;flex-wrap:wrap">
   <input type=file id=wlfile accept=".txt,.csv,text/plain,text/csv" onchange="wlReadFile(this)" style="flex:1;min-width:200px;font-size:12px">
   <button onclick="wlPreview()">${t('wl_imp_preview')}</button></div>
  <div id=wlres style="margin-top:12px"></div></div>`;}
function wlReadFile(inp){let f=inp.files&&inp.files[0];if(!f)return;
 if(f.size>200000){document.getElementById('wlres').innerHTML='<div class=meta style="color:#f85149">'+t('wl_imp_toobig')+'</div>';return;}
 let rd=new FileReader();rd.onload=()=>{document.getElementById('wlta').value=rd.result||'';};rd.readAsText(f);}
async function wlPreview(){let res=document.getElementById('wlres');res.innerHTML='<div class=meta>…</div>';
 let text=document.getElementById('wlta').value||'';
 let d=await(await fetch('/api/wishlist/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:text})})).json();
 if(!d.ok){res.innerHTML='<div class=meta style="color:#f85149">'+((d.msg||t('st_error')).replace(/</g,'&lt;'))+'</div>';return;}
 window._wlprev=d.entries;
 let sum=Object.keys(d.counts||{}).map(k=>`${t(WLST[k]?WLST[k][1]:k)}: <b>${d.counts[k]}</b>`).join(' · ');
 let warn=d.truncated?`<div class=meta style="color:#d29922">${t('wl_imp_trunc').replace('{n}',d.max)}</div>`:'';
 let nochk=d.checked?'':`<div class=meta style="color:#58a6ff">${t('wl_imp_nocheck')}</div>`;
 let rows=d.entries.map((e,i)=>{let st=WLST[e.status]||['#8b929e',e.status];
  let sel=e.status==='ambiguous'
   ?`<select id="wlc${i}" style="background:#1a1d23;color:#e6e8ec;border:1px solid #2a2f37;border-radius:6px;padding:3px 6px;font-size:12px">`
    +e.candidates.map(c=>`<option>${c.replace(/</g,'&lt;')}</option>`).join('')+'</select>'
   :`<span>${(e.title||'').replace(/</g,'&lt;')}</span>`;
  let skip=(e.status==='duplicate'||e.status==='in_library');
  return `<div class=job><div style="display:flex;align-items:center;gap:8px;flex:1">
    <input type=checkbox id="wlk${i}" ${skip?'':'checked'} ${skip?'disabled':''}>
    ${sel}<span class=meta style="font-size:11px">${(e.platform||'—').replace(/</g,'&lt;')}</span></div>
   <span style="color:${st[0]};font-size:12px">${t(st[1])}</span></div>`;}).join('');
 res.innerHTML=`<div class=meta style="margin-bottom:6px">${sum}</div>${warn}${nochk}
  <div style="max-height:320px;overflow:auto">${rows}</div>
  <div class=frow style="justify-content:flex-end;gap:8px"><span id=wlmsg class=meta></span>
   <button onclick="wlApply()">${t('wl_imp_apply')}</button></div>`;}
async function wlApply(){let prev=window._wlprev||[];let out=[];
 prev.forEach((e,i)=>{let k=document.getElementById('wlk'+i);if(!k||!k.checked)return;
  let c=document.getElementById('wlc'+i);
  out.push({title:c?c.value:e.title,platform:e.platform||''});});
 if(!out.length){document.getElementById('wlmsg').textContent=t('wl_imp_none');return;}
 let d=await(await fetch('/api/wishlist/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirm:true,entries:out})})).json();
 document.getElementById('wlmsg').textContent=t('wl_imp_done').replace('{a}',d.added||0).replace('{s}',d.skipped||0);
 loadJobs();}
// --- Discover / Startseite: beliebte Spiele je Konsole ---
async function loadDiscover(){let hint=document.getElementById('hint');hint.style.display='';hint.textContent=t('loading_home');
 let g=document.getElementById('grid');
 let rows=await(await fetch('/api/discover/rows')).json();window.DROWS=rows;
 if(!rows.length){hint.textContent=t('hint_type');g.className='';g.innerHTML='';return;}
 hint.style.display='none';g.className='disc';g.innerHTML='';
 let hid=new Set(JSON.parse(localStorage.getItem('dischide')||'[]'));
 let bar=document.createElement('div');bar.style.cssText='display:flex;justify-content:flex-end;margin-bottom:6px';
 bar.innerHTML='<button onclick="toggleDiscCust()" style="background:#1e2229;border:1px solid #2c323b;color:#8b929e;padding:5px 10px;border-radius:8px;cursor:pointer;font-size:12px">⚙ anpassen / customize</button>';
 g.appendChild(bar);
 let cust=document.createElement('div');cust.id='disccust';cust.style.cssText='display:none;background:#171a20;border-radius:8px;padding:10px;margin-bottom:12px';
 rows.forEach(r=>{let lbl=document.createElement('label');lbl.style.cssText='font-size:12px;color:#8b929e;display:inline-flex;gap:5px;align-items:center;margin:0 12px 6px 0';
  let cb=document.createElement('input');cb.type='checkbox';cb.checked=!hid.has(r.key);
  cb.onchange=()=>{let h=new Set(JSON.parse(localStorage.getItem('dischide')||'[]'));cb.checked?h.delete(r.key):h.add(r.key);localStorage.setItem('dischide',JSON.stringify([...h]));loadDiscover();};
  lbl.appendChild(cb);lbl.appendChild(document.createTextNode(r.console));cust.appendChild(lbl);});
 g.appendChild(cust);
 rows.filter(r=>!hid.has(r.key)).forEach(r=>{let sec=document.createElement('div');sec.className='drow';
  let pre=r.reco?t('because_you')+' ':(r.slug?t('popular_on')+' ':'');
  sec.innerHTML=`<div class=rowh>${pre}<b>${(r.console||'').replace(/</g,'&lt;')}</b> <span>· ${t('click_search')}</span></div><div class=strip></div>`;
  let strip=sec.querySelector('.strip');
  r.games.forEach(it=>{let c=document.createElement('div');c.className='pcard';
   // Fremde Bewertung auf der Karte (#210): mit Quelle beschriftet, sonst liest man sie
   // als die EIGENE — und das wird falsch, sobald daneben eigene Bewertungen stehen.
   // Ohne Wert steht dort nichts; eine erfundene Null wäre schlimmer als eine Lücke.
   let ext=it.ext_rating?`<span class=extrate title="IGDB">★ ${it.ext_rating}</span>`:'';
   c.innerHTML=`<div class=pcover style="${it.cover?`background-image:url('${it.cover}')`:''}">${it.in_library?'<span class=have2>✓</span>':''}${ext}</div><div class=pt>${it.title.replace(/</g,'&lt;')}</div>`;
   c.onclick=()=>{SELP=r.slug?new Set([r.slug]):new Set();
    localStorage.setItem('romp',JSON.stringify([...SELP]));updateFLabel();
    document.querySelectorAll('.chip').forEach(e=>e.classList.toggle('on',SELP.has(e.dataset.s)));
    document.getElementById('q').value=it.title;search();};
   strip.appendChild(c);});
  g.appendChild(sec);});}
function toggleDiscCust(){let e=document.getElementById('disccust');e.style.display=e.style.display=='none'?'block':'none';}
const STCLS={downloading:'downloading',importing:'importing',done:'done',error:'error',denied:'error'};
// Zustandsgruppen für den Filter (#201). Die Zustände gab es längst — sie waren nur nicht
// gruppiert, und die Seite war eine einzige chronologische Liste.
//
// WOHIN `denied` GEHÖRT (die offene Frage im Issue): in eine **eigene** Gruppe. Unter
// „fehlgeschlagen" würde man nach Defekten suchen und fände Entscheidungen; unter
// „erledigt" wäre es zwar richtig einsortiert, aber nicht mehr auffindbar — und genau
// das war die erste Rückmeldung aus der Benutzung. Abgelehnt ist ein eigener Ausgang:
// beendet, ohne Ergebnis, ohne Defekt.
const JOBGRUPPEN={
 aktiv:    ['pending','queued','approved','downloading','importing'],
 erledigt: ['done'],
 abgelehnt:['denied'],
 fehler:   ['error']};
function jobGruppe(state){
 for(const [g,zust] of Object.entries(JOBGRUPPEN))if(zust.includes(state))return g;
 return 'aktiv';}
// Was der Zähler an „Anfragen" zählt (#198). NICHT „was existiert", sondern „was ist
// unerledigt": laufende Aufträge UND Fehler. Fehler bleiben drin, weil ein Zähler, aus
// dem ein Fehlschlag herausfällt, dem Benutzer beibringt, dass Null „alles gut" heißt —
// dabei liegt dann etwas ungelöst herum. Die FARBE trennt beides: rot, sobald ein Fehler
// dabei ist. Abgelehntes zählt nicht: das war eine Entscheidung, keine offene Sache.
function jobOffen(o){return ['aktiv','fehler'].includes(jobGruppe(o.state));}
function stlab(s){return [t('st_'+s)||s, STCLS[s]||''];}
// Von der Anfrage zur Karte des Spiels (#390).
//
// WARUM UEBER DIE SUCHE UND NICHT DIREKT: Ein Auftrag traegt nur Titel und Plattform —
// keine Kennung, kein Cover, keine Fassungsliste. Die Detailansicht erwartet einen
// Suchtreffer. Deshalb wird gesucht und der beste Treffer geoeffnet.
//
// UND WARUM ERST BEIM KLICK: Ob ein Titel sich aufloesen laesst, weiss man erst nach einer
// Abfrage. Sie fuer jede Zeile beim Zeichnen zu stellen waere eine Anfrage je Auftrag —
// bei 50 Anfragen 50 Abfragen, nur damit ein Mauszeiger richtig aussieht.
//
// Findet die Suche nichts, sagt die Zeile das kurz. Ein leeres Fenster zu oeffnen waere
// schlechter als gar nichts: Der wahrscheinlichste Klick ist der auf eine FEHLGESCHLAGENE
// Anfrage, und die kann sehr wohl unauffindbar sein.
// KURZMELDUNGEN LEBEN NICHT IN DER ZEILE. (#459)
//
// `openJobDetail` schrieb seine Antwort in die `.jobmsg` DER ZEILE. Die Zeile ueberlebt
// das naechste Auffrischen nicht — `loadJobs` baut `#jobs` neu auf, und die Meldung ist
// weg, unter Umstaenden im selben Augenblick, in dem sie erschien. Der Nutzer klickt,
// etwas flackert oder nichts, und er kann einen funktionierenden Klick nicht von einem
// kaputten unterscheiden.
//
// Deshalb: Die Meldung steht HIER, nach Auftrags-Id, mit eigenem Ablauf. `loadJobs` traegt
// sie beim Zeichnen wieder ein. Ein Neuaufbau kann sie damit nicht mehr verlieren, und die
// vier Sekunden laufen ab dem KLICK, nicht ab dem letzten Neuzeichnen.
//
// EN: transient row messages live in this map keyed by job id, not in the row itself — a
// rebuild replaces the row and used to take the message with it.
const JOBMELDUNG=new Map();   // jid -> {text, bis}
function jobMeldungSetzen(jid,text,dauer=4000){
 if(!jid)return;
 JOBMELDUNG.set(jid,{text,bis:Date.now()+dauer});
 jobMeldungenAnwenden();
 setTimeout(()=>{let m=JOBMELDUNG.get(jid);
  if(m&&m.bis<=Date.now()){JOBMELDUNG.delete(jid);jobMeldungenAnwenden();}},dauer+50);}
function jobMeldungenAnwenden(){
 let jetzt=Date.now();
 document.querySelectorAll('#jobs [data-jid]').forEach(zeile=>{
  let m=JOBMELDUNG.get(zeile.dataset.jid);
  if(m&&m.bis<=jetzt){JOBMELDUNG.delete(zeile.dataset.jid);m=null;}
  let feld=zeile.querySelector('.jobmsg');
  if(feld)feld.textContent=m?m.text:'';});}

async function openJobDetail(titel, plattform, el){
 let jid=el&&el.dataset?el.dataset.jid:'';
 if(el){el.dataset.busy='1';el.style.opacity='.6';}
 try{
  let u='/api/search?q='+encodeURIComponent(titel)+(plattform?'&platforms='+encodeURIComponent(plattform):'');
  let a=await fetch(u);
  if(!a.ok)throw new Error('HTTP '+a.status);
  let d=await a.json();
  let treffer=(d||[]).find(x=>norm(x.title||'')===norm(titel))||(d||[])[0];
  if(!treffer){jobMeldungSetzen(jid,t('job_no_card'));return;}
  window.LASTRES=d;
  openDetail(treffer);
 }catch(e){
  // KEIN STILLES SCHEITERN. (#459) Hier stand ein leerer `catch`: Netzfehler, kaputtes
  // JSON oder ein 500 aus `/api/search` liessen die Zeile aufhellen und sonst NICHTS
  // geschehen — von einem toten Knopf nicht zu unterscheiden.
  jobMeldungSetzen(jid,t('job_lookup_failed'));
 }finally{
  if(el){delete el.dataset.busy;el.style.opacity='';}
 }}
let JOBGRP='';   // '' = alle; sonst aktiv|erledigt|fehler
// Was zuletzt gezeichnet wurde. Nicht nur die Daten: Dieselben Anfragen ergeben unter einem
// anderen FILTER eine andere Liste und in einer anderen SPRACHE andere Beschriftungen.
//
// Die Sprache gehoert ausdruecklich dazu. `setLang` ruft `loadJobs()` auf, um die Liste in
// der neuen Sprache zu zeichnen — ein Vergleich nur ueber die Daten haette diesen Aufruf
// verschluckt, und die Anfragenliste waere als einzige Ansicht in der alten Sprache stehen
// geblieben. (#419)
// EN: the key covers filter and language too; setLang() re-renders through this path, and
// comparing data alone would have left this one view untranslated.
let JOBSTAND='';
async function loadJobs(){let r=await fetch('/api/jobs');let d=await r.json();let j=document.getElementById('jobs');
 // NICHT NEU ZEICHNEN, WENN SICH NICHTS GEAENDERT HAT. (#419)
 //
 // Die Ansicht frischt alle 4 Sekunden auf und ersetzte dabei die ganze Liste — auch auf
 // einer stillen Instanz, auf der sich nichts bewegt. Jede dieser Ersetzungen ist ein
 // Fenster, in dem ein Klick ins Leere geht: Die Zeile, auf die der Nutzer zielt, wird
 // gerade abgehaengt, `onclick` laeuft nicht, und es passiert NICHTS — keine Karte, keine
 // Meldung, kein Fehler. Zweimal klicken half, aber das weiss niemand.
 //
 // Nebenwirkung derselben Ursache: `openJobDetail` schreibt „keine Karte" in die Zeile und
 // loescht sie nach 4 Sekunden wieder. Das Auffrischen konnte sie nach einer wegwischen.
 //
 // Das Fenster ist damit nicht zu, aber es steht nur noch offen, wenn sich wirklich etwas
 // bewegt hat — statt im Viersekundentakt fuer immer.
 // EN: re-rendering the whole list every 4 s created a window where clicks hit a node being
 // detached and silently did nothing. Skip the render when nothing changed.
 let stand=JSON.stringify([d,window.jobFilter||'',JOBGRP,LANG]);
 if(stand===JOBSTAND&&j.childElementCount)return;
 JOBSTAND=stand;
 j.innerHTML='';
 let alle=d;
 // Zustand zuerst, Nutzer danach — so wird die Seite gelesen: „läuft noch was, ist was
 // kaputt", und erst dann „von wem". Beide Filter greifen zusammen. (#201)
 let zahl=g=>alle.filter(o=>jobGruppe(o.state)===g&&(!window.jobFilter||(o.user||'—')===window.jobFilter)).length;
 let leiste=document.createElement('div');
 leiste.style.cssText='margin:0 0 10px;display:flex;flex-wrap:wrap;gap:6px;align-items:center';
 let gruppen=[['',t('flt_all'),alle.filter(o=>!window.jobFilter||(o.user||'—')===window.jobFilter).length],
              ['aktiv',t('flt_active'),zahl('aktiv')],
              ['erledigt',t('flt_done'),zahl('erledigt')],
              ['abgelehnt',t('flt_denied'),zahl('abgelehnt')],
              ['fehler',t('flt_failed'),zahl('fehler')]];
 // Zahl am Filter: die Seite sagt damit, was sie enthält, ohne dass man sie durchklickt.
 leiste.innerHTML=gruppen.map(g=>`<a class="ssub${JOBGRP===g[0]?' on':''}" onclick="JOBGRP='${g[0]}';loadJobs()">${g[1]} <b>${g[2]}</b></a>`).join('');
 // „Angezeigte entfernen" direkt bei den Anfragen: der Sammelknopf steckte bisher nur in
 // der Wartung, wo ihn niemand sucht, der die Zahl loswerden will. Nur für Endzustände. (#246)
 const GRP2ST={erledigt:['done'],abgelehnt:['denied'],fehler:['error']};
 if(canDo('manage_requests')&&GRP2ST[JOBGRP]&&zahl(JOBGRP))
  leiste.innerHTML+=`<button onclick="if(confirm(t('del_confirm')))admClearJobs(${JSON.stringify(GRP2ST[JOBGRP])})" style="margin-left:8px;background:#3a2b2b;border:none;color:#fff;padding:4px 10px;border-radius:6px;cursor:pointer;font-size:13px">${t('clear_group')}</button>`;
 if(canDo('manage_requests')){let users=[...new Set(alle.map(o=>o.user||'—'))].sort();
  if(users.length>1){
   let opts='<option value="">'+t('flt_all')+'</option>'+users.map(u=>`<option${window.jobFilter===u?' selected':''}>${u.replace(/</g,'&lt;')}</option>`).join('');
   leiste.innerHTML+=`<span style="margin-left:8px;color:var(--mut);font-size:13px">${t('flt_user')}:</span>`+
    `<select id=jobflt onchange="window.jobFilter=this.value;loadJobs()" style="background:#1a1d23;color:#e6e8ec;border:1px solid #2a2f37;border-radius:6px;padding:4px 8px">${opts}</select>`;}}
 j.appendChild(leiste);
 if(window.jobFilter)d=d.filter(o=>(o.user||'—')===window.jobFilter);
 if(JOBGRP)d=d.filter(o=>jobGruppe(o.state)===JOBGRP);
 if(!d.length){let h=document.createElement('div');h.className='hint';
  // „Es gibt keine Anfragen" und „in DIESEM Filter ist nichts" sind verschiedene Aussagen.
  // Vorher stand für beides derselbe Satz — der wäre jetzt schlicht falsch. (#201)
  h.textContent=(alle.length&&(JOBGRP||window.jobFilter))?t('flt_leer'):t('no_requests');
  j.appendChild(h);return;}
 d.forEach(o=>{let e=document.createElement('div');e.className='job';let L=stlab(o.state);let right;
  if(o.state=='pending'&&canDo('manage_requests')){
   right=`<button onclick="approveJob('${o.id}')" style="background:#1e5e3a;border:none;color:#fff;padding:5px 10px;border-radius:6px;cursor:pointer;margin-right:6px">${t('approve')}</button><button onclick="denyJob('${o.id}')" style="background:#6e2a2a;border:none;color:#fff;padding:5px 10px;border-radius:6px;cursor:pointer">${t('deny')}</button>`;
  }else{right=`<span class="st ${L[1]}">${L[0]}</span>`;
   if((o.state=='error'||o.state=='denied')&&canDo('manage_requests'))
    {// Ab dem dritten Versuch wechselt der Server die Quelle. Das gehört auf den Knopf,
     // sonst ist ein plötzlich anderes Ergebnis nicht erklärbar. (#200)
     let naechster=(o.tries||1)+1, wechsel=naechster>=3;
     right+=`<button onclick="retryJob('${o.id}')" style="background:#2a2f37;border:none;color:#fff;padding:5px 10px;border-radius:6px;cursor:pointer;margin-left:8px" title="${wechsel?t('retry_other_hint'):t('retry')}">↻ ${wechsel?t('retry_other'):t('retry')}</button>`;}
   // „Erneut einlesen" nur, wenn die Dateien wirklich noch liegen — ein Knopf, der beim
   // Drücken scheitert, ist schlimmer als keiner. Der Server sagt es je Auftrag. (#245)
   if(o.state=='error'&&o.reimportable&&canDo('manage_requests'))
    right+=`<button onclick="reimportJob('${o.id}')" style="background:#2a4a35;border:none;color:#fff;padding:5px 10px;border-radius:6px;cursor:pointer;margin-left:6px" title="${t('reimp_hint')}">⤵ ${t('reimp')}</button>`;
   // Entfernen nur in Endzuständen — eine laufende Anfrage darf nicht aus Versehen
   // verschwinden, während im Hintergrund noch geladen wird. (#246)
   if(['done','error','denied'].includes(o.state)&&canDo('manage_requests'))
    right+=`<button onclick="deleteJob('${o.id}',${o.reimportable?'true':'false'})" style="background:#3a2b2b;border:none;color:#fff;padding:5px 9px;border-radius:6px;cursor:pointer;margin-left:6px" title="${t('del_job')}">🗑</button>`;}
  // „fehlgeschlagen, 3. Versuch" sagt etwas anderes als „fehlgeschlagen". (#200)
  let vs=(o.tries||0)>1?` · ${o.tries}. ${t('try_n')}`:'';
  let dt=o.created?new Date(o.created*1000).toLocaleString():'';
  // Gelieferte Fassung im Verlauf zeigen — damit eine Falschlieferung belegbar ist. (#77)
  let vl=o.variant_label?` · 🏷 ${o.variant_label.replace(/</g,'&lt;')}`:'';
  e.innerHTML=`<div><div class=jobt style="cursor:pointer" title="${t('job_open_card')}">${o.title.replace(/</g,'&lt;')}</div><span class=jobmsg style="color:#8b929e;font-size:11px"></span><div class=meta style="color:#8b929e;font-size:11px">👤 <b style="color:#b9c0cc">${(o.user||'—').replace(/</g,'&lt;')}</b> · ${(o.platform||t('plat_unknown')).replace(/</g,'&lt;')} · ${o.source}${vs}${vl}${dt?' · '+dt:''} · ${o.msg||''}</div></div><div>${right}</div>`;
  // KEINE Bindung je Zeile mehr — der Titel traegt seine Daten, geklickt wird oben. (#449)
  e.dataset.titel=o.title; e.dataset.plattform=o.platform||'';
  e.dataset.jid=o.id;   // damit eine Kurzmeldung ihre Zeile wiederfindet (#459)
  j.appendChild(e);});
 jobKlickBindung(j);
 jobMeldungenAnwenden();}   // Kurzmeldungen ueberleben den Neuaufbau (#459)
// EIN Zuhoerer am BEHAELTER statt einer je Zeile. (#449)
//
// WARUM DAS DER UNTERSCHIED IST: `loadJobs` baut `#jobs` per `innerHTML` neu auf. Jede
// Zeile ist danach ein anderes Element — eine Bindung, die an der Zeile hing, ist weg, und
// ein Klick, der genau in diesen Moment faellt, tut NICHTS. Kein Fehler, keine Meldung.
//
// #419 hat die Zahl dieser Momente gesenkt (nicht neu zeichnen, wenn sich nichts geaendert
// hat) und ich habe daraus geschlossen, das Problem sei weg. War es nicht: Sobald sich
// wirklich etwas aendert, ist das Fenster wieder da — und beim Testfall aendert sich immer
// etwas, weil er die Anfrage gerade erst angelegt hat.
//
// Der Zuhoerer am Behaelter ueberlebt das Ersetzen, weil der Behaelter nicht ersetzt wird.
// Damit ist das Fenster nicht kleiner, sondern zu.
//
// EN: one listener on the container instead of one per row. innerHTML replacement detaches
// per-row handlers, so a click landing in that moment does nothing. #419 made those moments
// rarer; it could not remove them, because a list that never re-renders never updates.
function jobKlickBindung(behaelter){
 if(!behaelter||behaelter.dataset.klickgebunden)return;
 behaelter.dataset.klickgebunden='1';
 behaelter.addEventListener('click',ev=>{
  let titel=ev.target.closest('.jobt');if(!titel)return;
  let zeile=titel.closest('[data-titel]');if(!zeile||zeile.dataset.busy)return;
  openJobDetail(zeile.dataset.titel,zeile.dataset.plattform||'',zeile);
 });}
// --- Plattform-Vorauswahl ---
let SELP=new Set(JSON.parse(localStorage.getItem('romp')||'[]'));
let SLUGNAME={},GRUPPEN=[];
// Vorhandene Logos (#211): einmal fragen, dann weiss die Karte, ob es ein Bild gibt.
// Im Repo liegt keines — was hier ankommt, hat der Betreiber selbst hinterlegt. Ohne
// Datei bleibt es beim Namen, und das ist ein vollwertiger Zustand, kein Notbehelf.
let LOGOS=new Set();
async function ladeLogos(){
 try{let l=await(await fetch('/api/logos')).json();LOGOS=new Set(l||[]);}catch(e){}}
function plattformMarke(slug){
 let name=SLUGNAME[slug]||slug||'?';
 let sicher=String(name).replace(/</g,'&lt;');
 if(slug&&LOGOS.has(String(slug).toLowerCase()))
  return`<img class=logo src="/logo/${encodeURIComponent(slug)}" alt="${sicher}" title="${sicher}">`;
 return sicher;}
// Favoriten einmal holen und merken: die Karte fragt sonst je Titel nach, und die Liste
// ist klein genug, um sie im Kopf zu behalten. Nach jeder Änderung neu einlesen. (#207)
let FAVS=new Set();
async function ladeFavs(){
 if(!window.ROLE){FAVS=new Set();return;}
 try{let f=await(await fetch('/api/favourites')).json();
  FAVS=new Set((f||[]).map(e=>norm(e.title||'')));}catch(e){}}
// Dieselbe Normalisierung wie im Server (norm()): sonst gilt „Micro Mages" als etwas
// anderes als „Micro Mages (USA)" — bzw. schlimmer, umgekehrt.
function norm(x){return String(x||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();}
async function toggleFav(it,btn){
 let n=norm(it.title||'');
 let drin=FAVS.has(n);
 await fetch('/api/favourites'+(drin?'/remove':''),{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({title:it.title,platform:it.platform_slug||''})});
 drin?FAVS.delete(n):FAVS.add(n);
 if(btn){btn.classList.toggle('on',!drin);btn.textContent=(!drin?'♥ ':'♡ ')+t('favourite');}
 if(cur==='lists')loadLists();}
async function loadPlatforms(){
 let r=await fetch('/api/platforms');let d=await r.json();
 d.forEach(g=>g.items.forEach(it=>{SLUGNAME[it.slug]=it.name;}));
 // Dieselbe Gruppierung wie die Filterleiste — PLATFORMS liegt im Server und wird hier
 // nur weitergereicht. Eine zweite Liste würde irgendwann von der ersten abweichen. (#199)
 GRUPPEN=d.map(g=>({name:g.group,slugs:g.items.map(x=>x.slug)}));
 document.getElementById('filter').innerHTML=d.map(g=>`<div class=grp><div class=gl>${g.group}</div>`+
   g.items.map(it=>`<span class="chip${SELP.has(it.slug)?' on':''}" data-s="${it.slug}" onclick="toggleChip('${it.slug}')" title="${it.usenet?'auch über Usenet':'nur Archive.org'}">${it.name}${it.usenet?' 📡':''}</span>`).join('')+
   `</div>`).join('')+`<div class=fbtns><button onclick="clearP()">${t('reset')}</button></div>`;
 updateFLabel();}
function toggleChip(s){SELP.has(s)?SELP.delete(s):SELP.add(s);
 localStorage.setItem('romp',JSON.stringify([...SELP]));
 document.querySelectorAll('.chip[data-s="'+s+'"]').forEach(e=>e.classList.toggle('on',SELP.has(s)));
 updateFLabel();}
function clearP(){SELP.clear();localStorage.setItem('romp','[]');
 document.querySelectorAll('.chip').forEach(e=>e.classList.remove('on'));updateFLabel();}
function updateFLabel(){let e=document.getElementById('tF');if(e)e.textContent='🎛 '+t('platforms')+': '+(SELP.size?SELP.size+' '+t('selected'):t('all'));}
function toggleFilter(){let f=document.getElementById('filter');f.style.display=f.style.display=='block'?'none':'block';}
// --- Benutzerverwaltung ---
function canDo(perm){return window.ROLE=='admin'||(window.PERMS||[]).includes(perm);}
function defAvatar(name){let n=(name||'?').trim()||'?';let ini=(n[0]||'?').toUpperCase();
 let cols=['#5b8cff','#e0679a','#5bbf8a','#d9a441','#9b6dd6','#4bb7c6'];let c=cols[(n.charCodeAt(0)||0)%cols.length];
 let svg='<svg xmlns="http://www.w3.org/2000/svg" width="66" height="66"><rect width="66" height="66" rx="33" fill="'+c+'"/><text x="33" y="45" font-size="34" text-anchor="middle" fill="#fff" font-family="sans-serif">'+ini+'</text></svg>';
 return 'data:image/svg+xml;base64,'+btoa(unescape(encodeURIComponent(svg)));}
async function loadAuth(){let d=await(await fetch('/api/auth/status')).json();
 window.ROLE=d.role;window.VERSION=d.version||'';window.PERMS=d.perms||[];window.ME=d.user||'';
 let lang=d.user_lang||localStorage.getItem('lang')||d.default_lang||'de';
 if(lang!=LANG){LANG=lang;localStorage.setItem('lang',lang);setLang(lang);}
 applyDesign(d.user_design||localStorage.getItem('design')||d.default_design||'seerr');
 // Name und Bild wandern in den Knopf oben rechts (#206). `_who` merkt sich das
 // Markup, damit ein Sprachwechsel die Kopfleiste neu zeichnen kann, ohne /api/auth/status
 // erneut zu fragen.
 if(d.user){let nm=(d.display_name||d.user);
   window._who=`<img alt="" src="${d.avatar||defAvatar(nm)}">`+nm.replace(/</g,'&lt;')+' <span style="opacity:.7">▾</span>';}
 else window._who='';
 let ubox=document.getElementById('userbox');if(ubox)ubox.style.display=d.user?'':'none';
 zeichneKopf();
 if(d.role=='admin'){document.getElementById('nSet').style.display='';
   try{let cs=await(await fetch('/api/settings')).json();if(!cs.onboarded)startWizard();}catch(e){}}
 cfgWarn();zeichneFuss();ladeFavs();updateJobBadge();ladeLogos();}
// --- Eigene Bewertung und Kommentare (#210) ---
// Getrennt von der IGDB-Zahl: die eine ist der Presseschnitt, die andere die Meinung
// dieses Haushalts. Nebeneinander als dieselbe Sterne-Zahl wären sie nicht mehr
// auseinanderzuhalten — deshalb hier „deine" gegen „andere", und auf der Karte die
// fremde ausdrücklich mit Quelle.
async function loadTitleMeta(it){
 let box=document.getElementById('mrate');if(!box)return;
 let titel=window._detname||it.title||'';
 let d={};try{d=await(await fetch('/api/titlemeta?title='+encodeURIComponent(titel))).json();}catch(e){return;}
 let sterne=n=>[1,2,3,4,5].map(i=>`<span class="star${i<=n?' on':''}" onclick="setRating(${i})">★</span>`).join('');
 let andere=(d.others||[]).map(o=>`<span class=meta style="margin-right:10px">${o.user.replace(/</g,'&lt;')}: ${'★'.repeat(o.stars||0)}</span>`).join('');
 let komm=(d.comments||[]).map(k=>`<div class=frow style="align-items:flex-start"><div>
   <div class=meta style="font-size:11px">${k.user.replace(/</g,'&lt;')} · ${new Date((k.ts||0)*1000).toLocaleString()}</div>
   <div>${(k.text||'').replace(/</g,'&lt;')}</div></div></div>`).join('');
 box.innerHTML=`<h3>${t('rate_title')}</h3>
  <div class=frow><span style="min-width:150px">${t('rate_mine')}</span>
   <span id=mystars>${sterne(d.mine||0)}</span>
   ${d.mine?`<button onclick="setRating(0)" style="margin-left:10px;background:#2a2f37;border:none;color:#8b929e;padding:4px 9px;border-radius:6px;cursor:pointer;font-size:12px">${t('rate_clear')}</button>`:''}</div>
  ${andere?`<div class=frow><span style="min-width:150px">${t('rate_others')}</span><span>${andere}</span></div>`:''}
  <h3 style="font-size:13px;margin-top:14px">${t('comments')}</h3>
  ${komm||`<div class=meta>${t('comments_none')}</div>`}
  <div class=frow><input id=knew placeholder="${t('comment_ph')}"><button onclick="addComment()">${t('add_btn')}</button></div>`;}
async function setRating(n){
 let it=window._detit;if(!it)return;
 await fetch('/api/titlemeta/rating',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({title:window._detname||it.title||'',stars:n})});
 loadTitleMeta(it);}
async function addComment(){
 let it=window._detit,el=document.getElementById('knew');if(!it||!el||!el.value.trim())return;
 await fetch('/api/titlemeta/comment',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({title:window._detname||it.title||'',text:el.value})});
 el.value='';loadTitleMeta(it);}

// --- Meine Listen: Wunschliste und Favoriten (#195/#207) ---
// Die Wunschliste wurde bisher IN die Anfragen-Seite gezeichnet — nicht aus einer
// Entscheidung heraus, sondern weil die Seite gerade danebenlag. Eine Anfrage ist etwas,
// worauf das System eine Antwort schuldet: sie hat einen Zustand, sie endet, und ein
// Verwalter sieht die aller Nutzer. Eine Wunschliste ist das Gegenteil — persoenlich,
// offen, nichts laeuft. Beides gehoert zur PERSON, deshalb steht es jetzt hier, neben
// dem Profil, und hat eine eigene Adresse.
//
// Zwei Listen, EIN Bereich, aber getrennte Speicher: die Wunschliste leert sich, wenn ein
// Titel eintrifft — genau ihr Zweck. Ein Favorit darf nie von selbst verschwinden. (#207)
let LISTE='wish';
async function loadLists(){
 let el=document.getElementById('lists');if(!el)return;
 let reiter=[['wish','⭐ '+t('wishlist')],['fav','♥ '+t('favourites')]];
 el.innerHTML=`<div class=setwrap><div class=setnav>`+
  reiter.map(r=>`<a class="snav${r[0]===LISTE?' on':''}" onclick="LISTE='${r[0]}';loadLists()">${r[1]}</a>`).join('')+
  `</div><div id=listinhalt></div></div>`;
 let c=document.getElementById('listinhalt');
 if(LISTE==='wish'){
  let wl=[];try{wl=await(await fetch('/api/wishlist')).json();}catch(e){}
  c.innerHTML=`<div class=rowh style="margin-bottom:8px;display:flex;align-items:center;gap:8px"><b>${t('wl_hint_head')}</b>`+
   `<button onclick="openWlImport()" style="margin-left:auto;background:#2a2f37;border:none;color:#e6e8ec;padding:5px 10px;border-radius:6px;cursor:pointer;font-size:12px">${t('wl_import')}</button></div>`;
  if(!wl.length){c.innerHTML+=`<div class=meta>${t('wl_empty')}</div>`;return;}
  wl.forEach(e=>{let row=document.createElement('div');row.className='job';
   row.innerHTML=`<div><div>${(e.title||'').replace(/</g,'&lt;')}</div><div class=meta style="font-size:11px">${(SLUGNAME[e.platform]||e.platform||'—').replace(/</g,'&lt;')}</div></div>`;
   let b=document.createElement('button');b.textContent=t('wl_remove');
   b.style.cssText='background:#6e2a2a;border:none;color:#fff;padding:5px 10px;border-radius:6px;cursor:pointer';
   b.onclick=async()=>{await fetch('/api/wishlist/remove',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:e.title,platform:e.platform})});loadLists();};
   row.appendChild(b);c.appendChild(row);});
 }else{
  let fv=[];try{fv=await(await fetch('/api/favourites')).json();}catch(e){}
  c.innerHTML=`<div class=meta style="margin-bottom:8px">${t('fav_hint')}</div>`;
  if(!fv.length){c.innerHTML+=`<div class=meta>${t('fav_empty')}</div>`;return;}
  fv.forEach(e=>{let row=document.createElement('div');row.className='job';
   row.innerHTML=`<div><div>${(e.title||'').replace(/</g,'&lt;')}</div><div class=meta style="font-size:11px">${(SLUGNAME[e.platform]||e.platform||'—').replace(/</g,'&lt;')}</div></div>`;
   let b=document.createElement('button');b.textContent=t('fav_remove');
   b.style.cssText='background:#6e2a2a;border:none;color:#fff;padding:5px 10px;border-radius:6px;cursor:pointer';
   b.onclick=async()=>{await fetch('/api/favourites/remove',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:e.title})});loadLists();};
   row.appendChild(b);c.appendChild(row);});
 }}

// --- Fußzeile (#208) ---
// Die Version lag nur unter Einstellungen → Über: zwei Klicks tief und nur für Verwalter.
// Damit war die Frage aus #129 — „läuft hier das, was im Repo steht?" — zwar beantwortbar,
// aber nur auf Nachfrage. Hier steht sie, wo jeder Bildschirmauszug sie mitnimmt.
//
// ENTSCHIEDEN (die offene Frage im Issue): Der Repo-Link steht für alle, die **Version
// nur für Angemeldete**. Eine Versionsnummer auf der Anmeldeseite sagt einem Fremden,
// welche Lücken er nachschlagen kann — und der Preis dafür wäre kein Gewinn, weil ein
// Ausgeloggter mit der Nummer ohnehin nichts anfangen kann.
const REPO_URL='https://github.com/Sparxx947/romseerr';
async function zeichneFuss(){
 let f=document.getElementById('fuss');if(!f)return;
 let teile=[`<span>🎮 Romseerr</span>`,`<a href="${REPO_URL}" target=_blank rel="noopener noreferrer">GitHub</a>`];
 if(window.ROLE){
  let ver={};try{ver=await(await fetch('/api/version')).json();}catch(e){}
  let v=ver.version||window.VERSION||'';
  if(v)teile.splice(1,0,`<a href="${REPO_URL}/releases/tag/v${encodeURIComponent(v)}" target=_blank rel="noopener noreferrer">${v}</a>`);
  // Der Commit ist der Teil, der einen dev-Bau von dem Release unterscheidet, dessen
  // Versionsnummer er trägt — beide melden dieselbe Nummer. (#129)
  if(ver.commit)teile.push(`<span title="${(ver.built_at||'').replace(/"/g,'')}">${ver.commit.slice(0,7)}</span>`);
  if(ver.provenance&&ver.provenance!=='build')teile.push(`<span class=warn title="${t('about_no_build')}">⚠</span>`);
 }
 f.innerHTML=teile.join('<span style="opacity:.4">·</span>');}

// --- Konfigurationswarnungen (#197) ---
// Nur für Verwalter, weil nur die es beheben können, und nur wenn etwas kaputt ist.
// Der Meldungstext kommt SERVERSEITIG zweisprachig (DE/EN) — er nennt konkrete Pfade,
// die in keiner Übersetzungstabelle stehen können.
async function cfgWarn(){let el=document.getElementById('cfgwarn');if(!el)return;
 if(!(window.PERMS||[]).includes('manage_settings')&&window.ROLE!='admin'){el.style.display='none';return;}
 let w=[];try{w=(await(await fetch('/api/config/warnings')).json()).warnings||[];}catch(e){return;}
 if(!w.length){el.style.display='none';el.innerHTML='';return;}
 el.style.display='';
 el.innerHTML=`<b>⚠ ${t('cfg_warn')}</b> ${t('cfg_warn_hint')}`+
   w.map(x=>`<div class=w>${(x.text||'').replace(/</g,'&lt;')}`+
            (x.fix?`<br>→ ${x.fix.replace(/</g,'&lt;')}`:'')+`</div>`).join('');}
// --- Benutzerprofil (#23) ---
let PAV='';
async function openProfile(){let m=document.getElementById('modal');m.style.display='block';PAV='';
 let p=await(await fetch('/api/profile')).json();
 let inp='style="flex:1;min-width:120px;background:#0b0d10;border:1px solid #2c323b;color:#e6e8ec;padding:8px;border-radius:6px"';
 m.innerHTML=`<div class=box><button class=x onclick="closeModal()">×</button>
  <div class=sec><h3>${t('profile')} — ${(p.username||'').replace(/</g,'&lt;')}</h3>
   <div class=row><div id=pav style="width:66px;flex:0 0 66px;height:66px;border-radius:50%;background:#0b0d10 center/cover no-repeat;border:1px solid #2c323b;background-image:url('${p.avatar||defAvatar(p.display_name||p.username)}')"></div>
    <label style="flex:1;font-size:12px;color:#8b929e">${t('avatar')}<br><input type=file accept="image/*" onchange="pickAvatar(event)"></label></div>
   <div class=row><input id=pdn ${inp} placeholder="${t('display_name')}" value="${(p.display_name||'').replace(/"/g,'&quot;')}"></div>
   <div class=row><input id=pmail ${inp} placeholder="${t('email')}" value="${(p.email||'').replace(/"/g,'&quot;')}"></div>
   <div class=row><label style="color:#8b929e;font-size:13px">${t('language')}</label><select id=plang ${inp}><option value="">—</option><option value=de ${p.lang=='de'?'selected':''}>Deutsch</option><option value=en ${p.lang=='en'?'selected':''}>English</option><option value=fr ${p.lang=='fr'?'selected':''}>Français</option><option value=es ${p.lang=='es'?'selected':''}>Español</option><option value=it ${p.lang=='it'?'selected':''}>Italiano</option></select></div>
   <div class=row><label style="color:#8b929e;font-size:13px">${t('design')}</label><div style="display:flex;gap:8px;flex-wrap:wrap">${DESIGNS.map(dz=>`<button class="dpick${(p.design||'')==dz?' on':''}" data-d="${dz}" onclick="pickDesign('${dz}')">${t('d_'+dz)}</button>`).join('')}</div></div>
   <div class=row><input id=pwh ${inp} placeholder="${t('pwebhook')}" value="${(p.webhook||'').replace(/"/g,'&quot;')}"><button onclick="testPWebhook()">${t('test')}</button></div>
   <div class=row><input id=pra ${inp} placeholder="${t('ra_user')}" value="${(p.ra_user||'').replace(/"/g,'&quot;')}"></div>
   <div class=row><label style="color:#8b929e;font-size:13px;min-width:150px">${t('var_prefs')}</label>
    <div style="flex:1">${varPrefFields('p',p.variant||{},p.variant_regions||[])}</div></div>
   <div class=row><button onclick="saveProfile()">${t('save')}</button><span id=pmsg class=meta></span></div>
   <div class=row><button onclick="togglePush()" id=pushbtn>${t('push_enable')}</button><span id=pushmsg class=meta></span></div>
   <div class=row><span class=meta>Kontingent / Quota</span><span class=meta>${p.quota&&p.quota.enabled?(p.quota.remaining+' / '+p.quota.count+' ('+p.quota.days+'d)'):'—'}</span></div></div>
  <div class=sec><h3>${t('change_pw')}</h3>
   <div class=row><input id=pold type=password ${inp} placeholder="${t('cur_pw')}"><input id=pnew type=password ${inp} placeholder="${t('new_pw')}"></div>
   <div class=row><button onclick="changePw()">${t('change_pw')}</button><span id=pwmsg class=meta></span></div></div></div>`;
 refreshPushBtn();}
function urlB64ToU8(s){let pad='='.repeat((4-s.length%4)%4);let b=(s+pad).replace(/-/g,'+').replace(/_/g,'/');let raw=atob(b);let a=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)a[i]=raw.charCodeAt(i);return a;}
async function pushState(){if(!('serviceWorker'in navigator)||!('PushManager'in window)||!('Notification'in window))return 'unsupported';
 try{let reg=await navigator.serviceWorker.ready;let sub=await reg.pushManager.getSubscription();return sub?'on':'off';}catch(_){return 'unsupported';}}
async function refreshPushBtn(){let b=document.getElementById('pushbtn');if(!b)return;let st=await pushState();
 if(st=='unsupported'){b.textContent=t('push_unsupported');b.disabled=true;return;}
 b.disabled=false;b.textContent=st=='on'?t('push_disable'):t('push_enable');}
async function togglePush(){let msg=document.getElementById('pushmsg');let st=await pushState();
 if(st=='unsupported'){msg.textContent=t('push_unsupported');return;}
 let reg=await navigator.serviceWorker.ready;
 if(st=='on'){let sub=await reg.pushManager.getSubscription();
  if(sub){await fetch('/api/push/unsubscribe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({endpoint:sub.endpoint})});await sub.unsubscribe();}
  msg.textContent=t('push_off');refreshPushBtn();return;}
 let perm=await Notification.requestPermission();if(perm!='granted'){msg.textContent=t('push_denied');return;}
 let pk=await(await fetch('/api/push/pubkey')).json();if(!pk.enabled||!pk.key){msg.textContent=t('push_unsupported');return;}
 try{let sub=await reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:urlB64ToU8(pk.key)});
  await fetch('/api/push/subscribe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(sub)});
  msg.textContent=t('push_on');refreshPushBtn();}catch(e){msg.textContent=t('push_denied');}}
function pickAvatar(e){let f=e.target.files[0];if(!f)return;
 if(f.size>280000){document.getElementById('pmsg').textContent='max ~280 KB';return;}
 let r=new FileReader();r.onload=()=>{PAV=r.result;document.getElementById('pav').style.backgroundImage="url('"+PAV+"')";};r.readAsDataURL(f);}
function pickDesign(dz){applyDesign(dz);}
async function saveProfile(){let d={display_name:document.getElementById('pdn').value,email:document.getElementById('pmail').value,lang:document.getElementById('plang').value,design:document.documentElement.dataset.design||'',webhook:document.getElementById('pwh').value,ra_user:(document.getElementById('pra')||{}).value||'',variant:readVarPrefs('p')};
 if(PAV)d.avatar=PAV;
 let r=await(await fetch('/api/profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 document.getElementById('pmsg').textContent=r.ok?t('saved_ok'):(r.msg||t('st_error'));
 if(r.ok){PAV='';loadAuth();if(d.lang){LANG=d.lang;localStorage.setItem('lang',d.lang);setLang(d.lang);}}}
async function changePw(){let d={old:document.getElementById('pold').value,new:document.getElementById('pnew').value};
 let r=await(await fetch('/api/profile/password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 document.getElementById('pwmsg').textContent=r.ok?t('saved_ok'):(r.msg||t('st_error'));}
async function testPWebhook(){let wh=document.getElementById('pwh').value.trim();if(!wh)return;
 let r=await(await fetch('/api/profile/notify-test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:wh})})).json();
 document.getElementById('pmsg').textContent=r.ok?t('test_sent'):(r.msg||t('st_error'));}
// --- Admin-Bereich / Einstellungen (Seite mit Unterbereichen) ---
let SETSEC='general',SETSUB='';
// Zweite Menuebene (#202): Benachrichtigungen und Verbindungen stapelten je SECHS
// Verfahren untereinander — Telegram einrichten hiess an Discord vorbeiscrollen. Jetzt
// eine Seite je Verfahren. Produktnamen werden NICHT uebersetzt; sie heissen ueberall
// gleich, und ein uebersetztes "Discord" waere nur eine Fehlerquelle mehr.
// `zustand` beantwortet je Eintrag: eingerichtet? aktiv? — daraus wird der Punkt im Menue.
const SEK_SUB={
 notif:[['discord','Discord',    d=>({da:!!(d.discord||{}).url, an:!!(d.discord||{}).enabled})],
        ['smtp','E-Mail (SMTP)', d=>({da:!!(d.smtp||{}).host,   an:!!(d.smtp||{}).enabled})],
        ['telegram','Telegram',  d=>({da:!!((d.agents||{}).telegram||{}).chat, an:!!((d.agents||{}).telegram||{}).enabled})],
        ['webhook','Webhook',    d=>({da:!!((d.agents||{}).webhook||{}).url,   an:!!((d.agents||{}).webhook||{}).enabled})],
        ['gotify','Gotify',      d=>({da:!!((d.agents||{}).gotify||{}).url,    an:!!((d.agents||{}).gotify||{}).enabled})],
        ['ntfy','ntfy',          d=>({da:!!((d.agents||{}).ntfy||{}).topic,    an:!!((d.agents||{}).ntfy||{}).enabled})],
        ['pushover','Pushover',  d=>({da:!!((d.agents||{}).pushover||{}).user, an:!!((d.agents||{}).pushover||{}).enabled})],
        ['maillog',null,         ()=>({da:false,an:false}),'notif_maillog']],
 conn:[['sab','SABnzbd',        d=>({da:!!(d.connections||{}).sab_url,   an:!!(d.connections||{}).sab_url})],
       ['prow','Prowlarr',      d=>({da:!!(d.connections||{}).prow_url,  an:!!(d.connections||{}).prow_url})],
       ['igdb','IGDB',          d=>({da:!!(d.connections||{}).igdb_id,   an:!!(d.connections||{}).igdb_id})],
       ['scraper',null,         d=>({da:!!(d.connections||{}).ss_user,   an:!!(d.connections||{}).ss_user}),'conn_scraper'],
       ['romm','RomM',          d=>({da:!!(d.connections||{}).romm_url,  an:!!(d.connections||{}).romm_url})],
       ['ra','RetroAchievements',d=>({da:!!(d.connections||{}).has_ra_key,an:!!(d.connections||{}).has_ra_key})],
       ['archive','Archive.org', d=>({da:!!(d.connections||{}).ia_access,an:!!(d.connections||{}).ia_access})],
       ['jd','JDownloader',     d=>({da:!!(d.connections||{}).jd_dl_base,an:!!(d.connections||{}).jd_dl_base})],
       ['catalog',null,         d=>({da:!!(d.connections||{}).catalog_urls,an:!!(d.connections||{}).catalog_urls}),'cat_title'],
       ['stream',null,          d=>({da:!!((d.connections||{}).stream_url||(d.connections||{}).stream_url_2),an:!!((d.connections||{}).stream_url||(d.connections||{}).stream_url_2)}),'stream_title']]};
function subLabel(e){return e[3]?t(e[3]):e[1];}
function openSettingsView(){
 let secs=[['general',t('sec_general')],['notif',t('sec_notif')],['conn',t('sec_conn')],['users',t('sec_users')],['blocklist',t('blocklist')],['services',t('sec_services')],['drop',t('sec_drop')],['organize',t('sec_organize')],['maint',t('sec_maint')],['tls','HTTPS'],['about',t('sec_about')]];
 document.getElementById('settings').innerHTML='<div class=setwrap><div class=setnav>'+
  secs.map(x=>`<a class=snav data-sec="${x[0]}" onclick="setSection('${x[0]}')">${x[1]}</a>`).join('')+
  '</div><div id=setsub class=setsub style="display:none"></div><div id=setcontent></div></div>';
 setSection(SETSEC,SETSUB);}
// `ausRoute` wie bei openDetail: beim Klick kommt ein Verlaufseintrag dazu, beim
// Wiederherstellen aus der Adresse nicht. So ist auch eine Unterseite verlinkbar. (#194/#202)
function setSection(sec,sub,ausRoute){
 SETSEC=sec;
 let unter=SEK_SUB[sec]||null;
 SETSUB=unter?(unter.some(x=>x[0]===sub)?sub:unter[0][0]):'';
 document.querySelectorAll('.snav').forEach(e=>e.classList.toggle('on',e.dataset.sec==sec));
 let sb=document.getElementById('setsub');
 if(sb){
  sb.style.display=unter?'flex':'none';
  sb.innerHTML=unter?unter.map(e=>`<a class="ssub${e[0]===SETSUB?' on':''}" data-sub="${e[0]}" onclick="setSection('${sec}','${e[0]}')"><span class=dot></span>${subLabel(e)}</a>`).join(''):'';
  if(unter)subZustand(sec,unter);
 }
 if(!ausRoute&&cur==='set')routeSetzen('set',null,false,sec,SETSUB);
 let c=document.getElementById('setcontent');
 ({general:secGeneral,notif:secNotif,conn:secConn,users:secUsers,blocklist:secBlocklist,services:secServices,drop:secDrop,organize:secOrganize,maint:secMaint,tls:secTls,about:secAbout}[sec]||secGeneral)(c);}
// Der Zustand kommt aus /api/settings — dort stehen die Verbindungen OHNE Geheimnisse,
// genau richtig fuer die Frage "ist das eingerichtet?".
async function subZustand(sec,unter){
 let d={};try{d=await(await fetch('/api/settings')).json();}catch(e){return;}
 if(SETSEC!==sec)return;
 unter.forEach(e=>{
  let el=document.querySelector(`.ssub[data-sub="${e[0]}"] .dot`);if(!el)return;
  let z=(e[2]||(()=>({da:false,an:false})))(d)||{};
  el.className='dot'+(z.an?' an':(z.da?' aus':''));
  el.parentElement.title=z.an?t('sub_an'):(z.da?t('sub_da'):t('sub_leer'));});}
// Eine Seite je Dienst (#202). Die Speicherfunktion `saveConn` war schon tolerant —
// sie sendet nur Felder, die im DOM stehen (`if(!el)return`) — deshalb ist das Aufteilen
// hier gefahrlos: eine Teilsendung laesst die uebrigen Verbindungen unberuehrt.
async function secConn(c){
 let vals=await(await fetch('/api/settings/connections/reveal')).json();
 function fld(k,label,secret){let v=(vals[k]||'');
  let eye=secret?`<button type=button onclick="togEye('c_${k}',this)" title="${t('reveal')}" style="background:#2a2f37;border:none;color:#8b929e;padding:6px 9px;border-radius:6px;cursor:pointer;margin-left:6px">👁</button>`:'';
  return `<div class=frow><label style="min-width:150px">${label}</label><input id="c_${k}" ${secret?'type=password':''} value="${(''+v).replace(/"/g,'&quot;')}" style="flex:1">${eye}</div>`;}
 let fuss=`<div class=frow><button onclick="saveConn()">${t('save')}</button><button onclick="testConn()" style="margin-left:8px;background:#2a2f37">${t('test')}</button><span id=cmsg class=meta></span></div><div id=csvc style="margin-top:10px"></div>`;
 let seiten={
  sab:()=>`<h3>SABnzbd</h3>${fld('sab_url','URL')}${fld('sab_apikey','API-Key',1)}${fld('sab_cat','Kategorie / category')}${fuss}
  <div class=meta style="margin-top:14px;line-height:1.5">${t('un_hint')}<br>${t('un_grab')}</div>
  <div class=frow style="margin-top:6px"><button onclick="unCheck()" style="background:#2a2f37">${t('un_check')}</button></div>
  <div id=unres style="margin-top:8px"></div>`,
  prow:()=>`<h3>Prowlarr</h3>${fld('prow_url','URL')}${fld('prow_apikey','API-Key',1)}${fld('prow_cats','Kategorien / categories')}${fuss}`,
  igdb:()=>`<h3>IGDB</h3>${fld('igdb_id','Client-ID')}${fld('igdb_secret','Client-Secret',1)}${fuss}`,
  scraper:()=>`<h3>${t('conn_scraper')}</h3>${fld('sgdb_key','SteamGridDB-Key',1)}${fld('ss_user','ScreenScraper-User')}${fld('ss_pass','ScreenScraper-Passwort',1)}${fuss}`,
  archive:()=>`<h3>Archive.org</h3>
   <div class=meta style="margin-bottom:10px">${t('ia_hint')}</div>
   ${fld('ia_access','Access-Key')}${fld('ia_secret','Secret-Key',1)}${fuss}`,
  romm:()=>`<h3>RomM</h3>${fld('romm_url','URL')}${fld('romm_user','User')}${fld('romm_pass','Passwort / password',1)}${fuss}`,
  ra:()=>`<h3>RetroAchievements</h3>${fld('ra_key','API-Key',1)}
   <div class=frow><span class=meta id=rastat style="flex:1">…</span>
    <button type=button onclick="raRefresh()" style="background:#2a2f37">${t('ra_refresh')}</button></div>${fuss}`,
  jd:()=>`<h3>JDownloader</h3><div class=meta style="font-size:11px;margin-bottom:4px">${t('jd_hint')}</div>
   ${fld('jd_watch',t('jd_watch'))}${fld('jd_out',t('jd_out'))}${fld('jd_dl_base',t('jd_base'))}${fuss}
   <div class=meta style="margin-top:14px;line-height:1.5">${t('jd_probe_hint')}</div>
   <div class=frow style="margin-top:6px"><button onclick="jdProbe(this)" style="background:#2a2f37">${t('jd_probe')}</button></div>
   <div id=jdprobe style="margin-top:8px"></div>`,
  catalog:()=>`<h3>${t('cat_title')}</h3><div class=meta style="font-size:11px;margin-bottom:4px">${t('cat_hint')}</div>
   <div class=frow><label style="min-width:150px">${t('cat_urls')}</label>
    <textarea id=c_catalog_urls style="flex:1;min-height:60px;background:#0b0d10;border:1px solid #2c323b;color:#e6e8ec;padding:6px;border-radius:6px;font-family:ui-monospace,monospace;font-size:11px">${(vals['catalog_urls']||'').replace(/</g,'&lt;')}</textarea></div>
   <div class=frow><span class=meta id=catstat style="flex:1">…</span>
    <button type=button onclick="catRefresh()" style="background:#2a2f37">${t('cat_refresh')}</button></div>${fuss}`,
  stream:()=>`<h3>${t('stream_title')}</h3><div class=meta style="font-size:11px;margin-bottom:4px">${t('stream_hint')}</div>
   ${fld('stream_url',t('stream_url_l'))}${fld('stream_launch',t('stream_launch_l'),1)}
   <div class=meta style="font-size:11px;margin:8px 0 2px">${t('stream_seat2_hint')}</div>
   ${fld('stream_url_2',t('stream_url2_l'))}${fld('stream_launch_2',t('stream_launch2_l'),1)}
   <div class=frow><span class=meta id=emustat style="flex:1">…</span>
    <button type=button onclick="emuUpdate()" style="background:#2a2f37">${t('emu_update')}</button></div>
   <div class=meta style="font-size:11px;margin:6px 0 2px">${t('fw_hint')}</div>
   <div id=fwstat class=meta style="font-size:11px">…</div>
   <input type=file id=fwfile style="display:none">${fuss}`};
 c.innerHTML=`<div class=meta style="margin-bottom:10px">${t('conn_hint')}</div>`+(seiten[SETSUB]||seiten.sab)();
 // Nur der Statusabruf, der auf DIESER Seite gebraucht wird — vorher liefen alle vier
 // bei jedem Aufruf, auch fuer Bereiche, die gerade niemand ansieht.
 if(SETSUB==='ra')raStatus();
 if(SETSUB==='catalog')catStatus();
 if(SETSUB==='stream'){emuStatus();fwStatus();}}

// --- Firmware und BIOS auf dem Streaming-Host (#107) ---
// Bewusst je Plattform statt einer Sammelmeldung: "Firmware fehlt" hilft niemandem,
// "Dreamcast: dc_flash.bin fehlt" schon. Und ein Verweis auf die Anleitung des
// jeweiligen Projekts, damit der berechtigte Weg der sichtbare ist.
async function fwStatus(){let el=document.getElementById('fwstat');if(!el)return;
 let d={};try{d=await(await fetch('/api/stream/firmware')).json();}catch(e){}
 if(!d.platforms){el.textContent=t('fw_nolauncher');return;}
 if(d.vendor&&d.vendor.running){el.innerHTML=t('fw_fetching');setTimeout(fwStatus,5000);return;}
 el.innerHTML=d.platforms.map(p=>{
   let fehlt=p.files.filter(f=>f.state!=='ok');
   let farbe=p.ready?'#7ac57a':'#c9a227';
   let zeile=`<b style="color:${farbe}">${p.name}</b> `;
   if(p.ready){zeile+=t('fw_ready');}
   // Datei da, aber der Emulator hat sie nicht eingespielt: `fehlt` ist dann LEER, und
   // die alte Fassung schrieb an dieser Stelle nichts hin — die Plattform sah aus wie
   // ohne Befund. Genau dieser Zustand liess PS3 als vollstaendig erscheinen, waehrend
   // RPCS3 "Missing Firmware" protokollierte. (#162)
   else if(fehlt.length){zeile+=fehlt.map(f=>`${f.name}: ${f.state==='fehlt'?t('fw_missing'):t('fw_badsize')}`).join(', ');}
   else if(p.needs_install&&!p.installed){zeile+=t('fw_notinstalled');}
   else{zeile+=t('fw_missing');}
   zeile+=` · <a href="#" onclick="fwUpload('${p.platform}');return false" style="color:#7aa2f7">${t('fw_upload')}</a>`;
   if(p.vendor_fetch)zeile+=` · <a href="#" onclick="fwVendor('${p.platform}');return false" style="color:#7aa2f7">${t('fw_vendor')}</a>`;
   if(p.docs)zeile+=` · <a href="${p.docs}" target=_blank rel="noopener noreferrer" style="color:#8b93a1">${t('fw_docs')}</a>`;
   return zeile;}).join('<br>');}

async function fwUpload(plattform){let inp=document.getElementById('fwfile');if(!inp)return;
 inp.value='';inp.onchange=async()=>{let f=inp.files[0];if(!f)return;
  let el=document.getElementById('fwstat');el.textContent=t('fw_sending')+' '+f.name+' …';
  let fd=new FormData();fd.append('file',f);fd.append('platform',plattform);fd.append('name',f.name);
  try{let r=await fetch('/api/stream/firmware/upload',{method:'POST',body:fd});let j=await r.json();
   if(!j.ok){el.textContent=t('fw_failed')+(j.reason?' ('+j.reason+')':'');setTimeout(fwStatus,4000);return;}
  }catch(e){el.textContent=t('fw_failed');setTimeout(fwStatus,4000);return;}
  fwStatus();};
 inp.click();}

async function fwVendor(plattform){let el=document.getElementById('fwstat');el.textContent=t('fw_fetching');
 try{await fetch('/api/stream/firmware/vendor',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({platform:plattform})});}catch(e){}
 setTimeout(fwStatus,3000);}
// --- Emulatoren auf dem Streaming-Host: Stand + Aktualisierung (#71) ---
async function emuStatus(){let el=document.getElementById('emustat');if(!el)return;
 // Katalog statt bloßer Liste: eine frische Installation hat NICHTS, und der Betreiber
 // soll hier auswaehlen statt beim ersten Start ungefragt beladen zu werden. (#106)
 let c={};try{c=await(await fetch('/api/stream/emulators/catalog')).json();}catch(e){el.textContent=t('emu_nohost');return;}
 if(!c.ok){el.textContent=c.reason==='no_launcher'?t('emu_nolauncher'):t('emu_unreachable');return;}
 if(c.busy){el.innerHTML=t('emu_running')+(c.target?' ('+c.target+')':'');setTimeout(emuStatus,5000);return;}
 el.innerHTML=(c.catalog||[]).map(e=>{
   if(!e.installed){
     if(e.needs_url)return `<span class=meta title="${t('emu_needs_url')}">${e.name} <span style="opacity:.6">— ${t('emu_needs_url_kurz')}</span></span>`;
     return `${e.name} <a href="#" onclick="emuInstall('${e.dir}');return false" style="color:#3fb950">+ ${t('emu_install')}</a>`;
   }
   let v=e.version?' <span class=meta>('+e.version.replace(/</g,'&lt;')+')</span>':'';
   // Aktualisieren je Emulator (#338): Ein Sammellauf laedt hunderte Megabyte fuer
   // Emulatoren, die niemand benutzt, und wer eine Regression sucht, will genau einen
   // Schritt tun. Der Sammelknopf bleibt daneben bestehen.
   let up=` <a href="#" onclick="emuUpdate('${e.dir}');return false" title="${t('emu_update_one')}" style="color:#58a6ff">⟳</a>`;
   // Wie weit zurueck? Frueher gab es genau eine Fassung und der Pfeil sagte nichts
   // darueber. `kept` ist die Zahl der aufgehobenen Fassungen.
   let n=e.kept||0;
   let rb=e.can_rollback?` <a href="#" onclick="emuRollback('${e.dir}');return false" title="${t('emu_rb_title').replace('{n}',n).replace('{v}',(e.previous||'').replace(/"/g,''))}" style="color:#d29922">↩${n>1?'<span class=meta>'+n+'</span>':''}</a>`:'';
   return '<b>'+e.name+'</b>'+v+up+rb;}).join(' · ')
  ||t('emu_none');
 return;}
async function emuInstall(dir){let el=document.getElementById('emustat');el.textContent='…';
 let r=await fetch('/api/stream/emulators/install',{method:'POST',
   headers:{'Content-Type':'application/json'},body:JSON.stringify({name:dir})});
 if(r.status===409){el.textContent=t('emu_running');setTimeout(emuStatus,5000);return;}
 let d=await r.json();
 if(!d.ok){el.textContent=t('emu_unreachable');return;}
 setTimeout(emuStatus,3000);}
async function emuRollback(name){
 if(!confirm(t('emu_rb_confirm').replace('{n}',name)))return;
 let el=document.getElementById('emustat');el.textContent='…';
 let d=await(await fetch('/api/stream/emulators/rollback',{method:'POST',
   headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name})})).json();
 if(!d.ok){el.textContent=t('emu_rb_failed');return;}
 setTimeout(emuStatus,1500);}
async function emuUpdate(dir){let el=document.getElementById('emustat');el.textContent='…';
 // Ohne Argument laufen alle, mit einem genau der eine (#338).
 let r=await fetch('/api/stream/emulators/update',{method:'POST',
   headers:{'Content-Type':'application/json'},body:JSON.stringify(dir?{name:dir}:{})});
 if(r.status===409){el.textContent=t('emu_running');setTimeout(emuStatus,5000);return;}
 let d=await r.json();
 if(!d.ok){el.textContent=t('emu_unreachable');return;}
 setTimeout(emuStatus,3000);}
async function catStatus(){let el=document.getElementById('catstat');if(!el)return;
 let d=await(await fetch('/api/catalog/status')).json();
 if(!d.configured){el.textContent=t('cat_none');return;}
 el.innerHTML=d.sources.map(s=>`${(s.name||s.url).replace(/</g,'&lt;')}: `
  +(s.error?`<span style="color:#f85149">${s.error.replace(/</g,'&lt;')}</span>`
          :`${s.count||0} · ${t('cov_asof')} ${(s.fetched||'').slice(0,10)}`)).join('<br>')
  +`<br>${d.items} ${t('cat_items')}`
  +(d.jd&&!d.jd.ok?`<br><span style="color:#d29922">JDownloader: ${d.jd.info.replace(/</g,'&lt;')}</span>`:'');}
async function catRefresh(){let el=document.getElementById('catstat');el.textContent='…';
 let d=await(await fetch('/api/catalog/refresh',{method:'POST'})).json();
 if(!d.ok){el.textContent=d.msg||t('st_error');return;}setTimeout(catStatus,4000);}
async function raStatus(){let el=document.getElementById('rastat');if(!el)return;
 let d=await(await fetch('/api/ra/status')).json();
 if(!d.enabled){el.textContent=t('ra_nokey');return;}
 if(d.build&&d.build.running){el.textContent=`${d.build.current||''} ${d.build.done}/${d.build.total}`;setTimeout(raStatus,2000);return;}
 el.textContent=`${d.total} ${t('ra_sets')} · ${Object.keys(d.platforms||{}).length} ${t('about_platforms')}`
  +(d.snapshot?` · ${t('cov_asof')} ${d.snapshot.slice(0,10)}`:'')
  +((d.unmapped||[]).length?` · ${t('ra_unmapped')}: ${d.unmapped.join(', ')}`:'');}
async function raRefresh(){let el=document.getElementById('rastat');el.textContent='…';
 let d=await(await fetch('/api/ra/refresh',{method:'POST'})).json();
 if(!d.ok){el.textContent=d.msg||t('st_error');return;}setTimeout(raStatus,1500);}
function togEye(id,btn){let el=document.getElementById(id);if(!el)return;el.type=el.type=='password'?'text':'password';btn.style.color=el.type=='text'?'#e6e8ec':'#8b929e';}
async function secTls(c){let d=await(await fetch('/api/settings/tls')).json();
 let ta='flex:1;min-height:110px;background:#0b0d10;border:1px solid #2c323b;color:#e6e8ec;padding:8px;border-radius:6px;font-family:ui-monospace,monospace;font-size:11px';
 let status=d.has_cert?`✅ ${(d.cn||'').replace(/</g,'&lt;')} · ${t('tls_expires')} ${d.expires||'?'}`:`⬜ ${t('tls_none')}`;
 c.innerHTML=`<h3>HTTPS / TLS</h3><div class=meta style="margin-bottom:8px">${t('tls_hint')}</div>
  <div class=frow><span class=meta>${status}</span></div>
  <div class=frow><label style="min-width:auto"><input type=checkbox id=tls_en ${d.enabled?'checked':''}> ${t('active')}</label>
   <label style="min-width:auto;margin-left:16px">Port <input id=tls_port type=number value="${d.port||8443}" style="flex:0 0 100px"></label></div>
  <div class=frow><textarea id=tls_cert placeholder="-----BEGIN CERTIFICATE-----" style="${ta}"></textarea></div>
  <div class=frow><textarea id=tls_key placeholder="-----BEGIN PRIVATE KEY-----   (${t('tls_key_note')})" style="${ta}"></textarea></div>
  <div class=frow><button onclick="saveTls()">${t('save')}</button><button onclick="removeTls()" style="margin-left:8px;background:#6e2a2a">${t('del')}</button><span id=tmsg class=meta></span></div>`;}
async function saveTls(){let body={enabled:document.getElementById('tls_en').checked,port:parseInt(document.getElementById('tls_port').value)||8443};
 let cert=document.getElementById('tls_cert').value.trim(),key=document.getElementById('tls_key').value.trim();
 if(cert||key){body.cert=cert;body.key=key;}
 let r=await(await fetch('/api/settings/tls',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})).json();
 document.getElementById('tmsg').textContent=r.ok?(t('saved')+' — '+t('tls_restart')):(r.msg||t('st_error'));if(r.ok)setTimeout(()=>setSection('tls'),700);}
async function removeTls(){await fetch('/api/settings/tls/remove',{method:'POST'});setSection('tls');}
// --- Erststart-Assistent / onboarding wizard ---
const WIZ=[{svc:null},
 {svc:'SABnzbd',fields:[['sab_url','URL'],['sab_apikey','API-Key',1],['sab_cat','Kategorie / category']]},
 {svc:'Prowlarr',fields:[['prow_url','URL'],['prow_apikey','API-Key',1],['prow_cats','Kategorien / categories']]},
 {svc:'IGDB',fields:[['igdb_id','Client-ID'],['igdb_secret','Client-Secret',1]]},
 {svc:'RomM',fields:[['romm_url','URL'],['romm_user','User'],['romm_pass','Passwort / password',1]]},
 {svc:'done'}];
let wizIdx=0,wizVals={};
async function startWizard(){wizIdx=0;try{wizVals=await(await fetch('/api/settings/connections/reveal')).json();}catch(e){wizVals={};}renderWiz();}
function renderWiz(){let m=document.getElementById('modal');m.style.display='block';let s=WIZ[wizIdx];let total=WIZ.length-2;let body,btns;
 let bA='background:var(--acc);border:none;color:#fff;padding:8px 14px;border-radius:6px;cursor:pointer',bG='background:#2a2f37;border:none;color:#e6e8ec;padding:8px 14px;border-radius:6px;cursor:pointer';
 if(s.svc===null){body=`<h2>👋 ${t('wiz_welcome')}</h2><p class=meta style="line-height:1.6">${t('wiz_welcome_txt')}</p>`;
   btns=`<button onclick="wizFinish()" style="${bG}">${t('wiz_skip')}</button><button onclick="wizGo(1)" style="${bA};margin-left:8px">${t('wiz_next')} →</button>`;}
 else if(s.svc==='done'){body=`<h2>✅ ${t('wiz_done')}</h2><p class=meta style="line-height:1.6">${t('wiz_done_txt')}</p>`;
   btns=`<button onclick="wizFinish()" style="${bA}">${t('wiz_finish')}</button>`;}
 else{let inp='style="flex:1;min-width:120px;background:#0b0d10;border:1px solid #2c323b;color:#e6e8ec;padding:8px;border-radius:6px"';
   let fl=s.fields.map(f=>`<div class=frow><label style="min-width:130px">${f[1]}</label><input id="w_${f[0]}" ${f[2]?'type=password':''} value="${(''+(wizVals[f[0]]||'')).replace(/"/g,'&quot;')}" ${inp}></div>`).join('');
   body=`<div class=meta>${t('wiz_step')} ${wizIdx}/${total}</div><h2>${s.svc}</h2>${fl}<div class=frow><button onclick="wizTest('${s.svc}')" style="${bG};padding:6px 12px">${t('test')}</button><span id=wtest class=meta></span></div>`;
   btns=`<button onclick="wizGo(-1)" style="${bG}">← ${t('wiz_back')}</button><button onclick="wizSaveNext()" style="${bA};margin-left:8px">${t('wiz_next')} →</button><button onclick="wizGo(1)" style="background:transparent;border:1px solid #2c323b;color:#8b929e;padding:8px 14px;border-radius:6px;cursor:pointer;margin-left:8px">${t('wiz_skip')}</button>`;}
 m.innerHTML=`<div class=box><button class=x onclick="closeModal()">×</button><div class=sec>${body}</div><div class=sec style="display:flex;justify-content:flex-end">${btns}</div></div>`;}
function wizGo(dir){wizCollect();wizIdx=Math.max(0,Math.min(WIZ.length-1,wizIdx+dir));renderWiz();}
function wizCollect(){let s=WIZ[wizIdx];if(!s||!s.fields)return;s.fields.forEach(f=>{let el=document.getElementById('w_'+f[0]);if(el)wizVals[f[0]]=el.value;});}
async function wizSave(){let s=WIZ[wizIdx];if(!s.fields)return;let conn={};s.fields.forEach(f=>{conn[f[0]]=wizVals[f[0]]||'';});
 await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({connections:conn})});}
async function wizSaveNext(){wizCollect();await wizSave();wizGo(1);}
async function wizTest(svc){wizCollect();document.getElementById('wtest').textContent='…';await wizSave();
 let d=await(await fetch('/api/services/status')).json();let x=(d||[]).find(o=>o.name===svc);
 document.getElementById('wtest').textContent=x?((x.ok?'✅ ':'❌ ')+(x.info||'')):'—';}
async function wizFinish(){await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({onboarded:true})});closeModal();if(cur=='s')loadDiscover();}
const CONN_ALL=['sab_url','sab_apikey','sab_cat','prow_url','prow_apikey','prow_cats','igdb_id','igdb_secret','sgdb_key','ss_user','ss_pass','romm_url','romm_user','romm_pass','jd_watch','jd_out','jd_dl_base','ra_key','ia_access','ia_secret','catalog_urls','stream_url','stream_launch'];
const CONN_SEC=['sab_apikey','prow_apikey','igdb_secret','sgdb_key','ss_pass','romm_pass','ia_secret'];
async function saveConn(){let conn={};CONN_ALL.forEach(k=>{let el=document.getElementById('c_'+k);if(!el)return;
  if(CONN_SEC.includes(k)){if(el.value)conn[k]=el.value;}else{conn[k]=el.value;}});
 let r=await(await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({connections:conn})})).json();
 document.getElementById('cmsg').textContent=r.ok?t('saved'):t('st_error');if(r.ok)setTimeout(()=>setSection('conn'),400);}
async function testConn(){let b=document.getElementById('csvc');b.textContent='…';
 let d=await(await fetch('/api/services/status')).json();
 b.innerHTML=(d||[]).map(x=>`<div class=meta>${x.ok?'✅':'❌'} <b>${x.name}</b> ${(x.info||'').replace(/</g,'&lt;')}</div>`).join('');}
// Namen der Stufen aus /api/usenet/check. Der Server liefert stabile Schluessel, die
// Beschriftung kommt von hier — sonst waere die Diagnose einsprachig. (#196)
const UN_NAME={search:'un_search',category:'un_cat',queue:'un_queue',collect:'un_collect'};
// Die Übergabe wirklich ausprobieren, statt nur die eigene Hälfte zu bestätigen. (#218)
async function jdProbe(btn){
 let box=document.getElementById('jdprobe');if(box)box.textContent=t('jd_probe_run');
 if(btn)btn.disabled=true;
 let d={};try{d=await(await fetch('/api/jd/probe',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({wait:30})})).json();}catch(e){d={ok:false,info:t('st_error')};}
 if(btn)btn.disabled=false;
 if(!box)return;
 box.innerHTML=`<div class=meta>${d.ok?'✅':'❌'} ${(d.info||'').replace(/</g,'&lt;')}</div>`
  +(d.fix?`<div class=meta style="margin-top:4px;color:#d29922">→ ${d.fix.replace(/</g,'&lt;')}</div>`:'');}
async function unCheck(){let b=document.getElementById('unres');b.textContent='…';
 let d={};try{d=await(await fetch('/api/usenet/check')).json();}catch(e){b.textContent=t('st_error');return;}
 b.innerHTML=((d||{}).steps||[]).map(x=>`<div class=meta>${x.ok?'✅':'❌'} <b>${x.step.startsWith('indexer:')?t('un_indexer')+' '+x.step.slice(8).replace(/</g,'&lt;'):t(UN_NAME[x.step]||x.step)}</b> — ${(x.info||'').replace(/</g,'&lt;')}</div>`).join('')||`<div class=meta>${t('st_error')}</div>`;}
// Liegengebliebene Downloads: erst sichtbar machen, dann entfernbar. Ein Ordner, von dem
// niemand weiss, ist nicht aufgehoben, sondern verloren. (#244)
function mbFormat(b){return b>=1073741824?(b/1073741824).toFixed(1)+' GB':Math.round(b/1048576)+' MB';}
async function loadLeftovers(){
 let el=document.getElementById('lolist');if(!el)return;
 let d={};try{d=await(await fetch('/api/leftovers')).json();}catch(e){el.textContent=t('st_error');return;}
 let it=d.items||[];
 if(!it.length){el.innerHTML=`<div class=meta>${t('lo_none')}</div>${loDaysFeld(d.days)}`;return;}
 el.innerHTML=it.map(x=>`<div class=frow style="gap:8px;align-items:center;padding:4px 0;border-bottom:1px solid #2a2f37">
   <span style="flex:1;min-width:180px">${(x.title||x.name).replace(/</g,'&lt;')}</span>
   <span class=meta>${mbFormat(x.size)} · ${x.age_days} ${t('lo_age')}${x.state?' · '+t('st_'+x.state):''}</span>
   <button onclick="loRemove('${x.jid}')" style="background:#2a2f37">${t('lo_remove')}</button></div>`).join('')
  +`<div class=frow style="margin-top:8px;gap:8px;align-items:center"><b>${mbFormat(d.total||0)}</b>
    <button onclick="loRemove(null)" style="background:#7a2b2b">${t('lo_removeall')}</button></div>`
  +loDaysFeld(d.days);}
function loDaysFeld(v){return `<div class=frow style="margin-top:10px;gap:8px;align-items:center">
  <label style="min-width:200px">${t('lo_days')}</label>
  <input id=lodays type=number min=0 value="${v==null?14:v}" style="width:90px"
         onchange="loSaveDays(this.value)"></div>`;}
async function loSaveDays(v){
 await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({leftover_days:parseInt(v||0,10)})});}
async function loRemove(jid){
 if(!confirm(jid?t('lo_confirm'):t('lo_confirmall')))return;
 await fetch('/api/leftovers/remove',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify(jid?{jid:jid}:{all:true})});
 loadLeftovers();}
async function secMaint(c){
 c.innerHTML=`<h3>${t('sec_maint')}</h3><div id=mstats class=meta>…</div>
  <div style="margin:10px 0;display:flex;gap:8px;flex-wrap:wrap">
   <button onclick="admCache()">${t('clear_cache')}</button>
   <button onclick="admReindex()">${t('reindex')}</button>
   <button onclick="admClearJobs()">${t('clear_all_final')}</button>
   <button onclick="loadLogs()">${t('refresh')}</button>
   <span id=mmsg class=meta></span></div>
  <h3 style="margin-top:16px">${t('lo_title')}</h3>
  <div class=meta style="line-height:1.6;margin-bottom:8px">${t('lo_hint')}</div>
  <div id=lolist class=meta>…</div>
  <h3 style="margin-top:16px">${t('exp_title')}</h3>
  <div class=meta style="line-height:1.6;margin-bottom:8px">${t('exp_hint')}</div>
  <div class=frow style="gap:8px;flex-wrap:wrap">
   <label style="min-width:150px">${t('exp_pass')}</label>
   <input id=exppw type=password placeholder="${t('exp_pass_ph')}" style="flex:1;min-width:180px">
   <button onclick="doExport()">${t('exp_do')}</button></div>
  <div class=frow style="gap:8px;flex-wrap:wrap">
   <input type=file id=impfile accept=".json,application/json" style="flex:1;min-width:180px;font-size:12px">
   <select id=impmode style="background:#1a1d23;color:#e6e8ec;border:1px solid #2a2f37;border-radius:6px;padding:5px 8px">
    <option value="merge">${t('exp_merge')}</option><option value="replace">${t('exp_replace')}</option></select>
   <button onclick="doImport()" style="background:#6e2a2a">${t('imp_do')}</button></div>
  <div id=impmsg class=meta></div>
  <h3 style="margin-top:16px">${t('logs')}</h3><pre id=logbox class=logbox>…</pre>`;
 loadMStats();loadLogs();loadLeftovers();}
// --- Export/Import der Konfiguration (#75) ---
async function doExport(){let pw=(document.getElementById('exppw').value||'');
 let msg=document.getElementById('impmsg');msg.style.color='';msg.textContent='…';
 let body=pw?{secrets:'encrypt',passphrase:pw}:{};
 let r=await fetch('/api/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 let d=await r.json();
 if(!r.ok||d.ok===false){msg.style.color='#f85149';msg.textContent=d.msg||t('st_error');return;}
 let blob=new Blob([JSON.stringify(d,null,2)],{type:'application/json'});
 let a=document.createElement('a');a.href=URL.createObjectURL(blob);
 a.download='romseerr-export-'+(d.exported_at||'').replace(/[:]/g,'')+'.json';
 document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(a.href);
 msg.textContent=pw?t('exp_done_enc'):t('exp_done_plain');}
async function doImport(){let msg=document.getElementById('impmsg');msg.style.color='';
 let f=document.getElementById('impfile').files[0];
 if(!f){msg.style.color='#f85149';msg.textContent=t('imp_nofile');return;}
 let mode=document.getElementById('impmode').value;
 if(!confirm(t(mode==='replace'?'imp_conf_replace':'imp_conf_merge')))return;
 let doc;try{doc=JSON.parse(await f.text());}catch(e){msg.style.color='#f85149';msg.textContent=t('imp_badjson');return;}
 msg.textContent='…';
 let r=await fetch('/api/import',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({document:doc,mode:mode,passphrase:document.getElementById('exppw').value||''})});
 let d=await r.json();
 if(!d.ok){msg.style.color='#f85149';msg.textContent=d.msg||t('st_error');return;}
 msg.style.color='#3fb950';
 msg.textContent=t('imp_done')+' '+Object.keys(d.counts||{}).map(k=>k+': '+d.counts[k]).join(' · ');}
async function loadMStats(){let s=await(await fetch('/api/admin/stats')).json();
 document.getElementById('mstats').textContent=`${t('lbl_jobs')}: ${s.jobs_total} (${s.jobs_active} / ${s.jobs_finished}) · ${t('lbl_lib')}: ${s.lib_titles} (${s.lib_platforms}) · IGDB-Cache: ${s.igdb_cache}`;}
async function loadLogs(){let d=await(await fetch('/api/logs')).json();let b=document.getElementById('logbox');if(!b)return;b.textContent=(d.lines||[]).join('\n');b.scrollTop=b.scrollHeight;}
async function admCache(){await fetch('/api/admin/cache/clear',{method:'POST'});document.getElementById('mmsg').textContent=t('done_word');loadMStats();}
async function admReindex(){await fetch('/api/admin/reindex',{method:'POST'});document.getElementById('mmsg').textContent=t('done_word');setTimeout(()=>{loadMStats();loadLogs();},1800);}
async function admClearJobs(states){
 let r=await(await fetch('/api/jobs/clear-finished',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify(states?{states:states}:{})})).json();
 let el=document.getElementById('mmsg');if(el)el.textContent=t('done_word')+' ('+(r.removed||0)+')';
 if(typeof loadMStats==='function'&&document.getElementById('mstats'))loadMStats();
 loadJobs&&document.getElementById('jobs')&&loadJobs();updateJobBadge();}
async function secGeneral(c){let s=await(await fetch('/api/settings')).json();let gg=s.general||{};let qo=s.quota||{};
 c.innerHTML=`<h3>${t('sec_general')}</h3>
  <div class=frow><label>${t('app_name')}</label><input id=gname value="${(gg.app_name||'Romseerr').replace(/"/g,'&quot;')}"></div>
  <div class=frow><label>${t('default_lang')}</label><select id=glang><option value=de ${(gg.default_lang||'de')=='de'?'selected':''}>Deutsch</option><option value=en ${gg.default_lang=='en'?'selected':''}>English</option><option value=fr ${gg.default_lang=='fr'?'selected':''}>Français</option><option value=es ${gg.default_lang=='es'?'selected':''}>Español</option><option value=it ${gg.default_lang=='it'?'selected':''}>Italiano</option></select></div>
  <div class=frow><label>${t('default_design')}</label><select id=gdesign>${DESIGNS.map(dz=>`<option value="${dz}" ${(gg.default_design||'seerr')==dz?'selected':''}>${t('d_'+dz)}</option>`).join('')}</select></div>
  <button onclick="saveGeneral()">${t('save')}</button> <span id=gmsg class=meta></span>
  <h3 style="margin-top:20px">Kontingent / Quota</h3>
  <div class=frow><label style="min-width:auto"><input type=checkbox id=qen ${qo.enabled?'checked':''}> ${t('active')}</label><span></span></div>
  <div class=frow><input id=qcount type=number style="flex:0 0 90px" value="${qo.count||10}"><input id=qdays type=number style="flex:0 0 90px" value="${qo.days||7}"><span class=meta>Anfragen / X Tage · requests / X days</span></div>
  <button onclick="saveQuota()">${t('save')}</button> <span id=qmsg class=meta></span>
  <h3 style="margin-top:20px">${t('sec_outbound')}</h3>
  <div class=meta style="margin-bottom:6px;line-height:1.6">${t('outbound_hint')}</div>
  <label style="display:block;font-size:13px;color:#8b929e"><input type=checkbox id=gpriv ${s.allow_private_webhooks?'checked':''}
   onchange="savePrivate(this.checked)"> ${t('outbound_allow')}</label>
  <span id=privmsg class=meta></span>
  <h3 style="margin-top:20px">${t('var_prefs')}</h3>
  <div class=meta style="margin-bottom:6px;line-height:1.6">${t('var_hint')}</div>
  ${varPrefFields('g',s.variant||{},s.variant_regions||[])}
  <div style="margin-top:8px"><button onclick="saveVariant()">${t('save')}</button> <span id=vmsg class=meta></span></div>
  <h3 style="margin-top:20px">API-Key</h3>
  <div class=frow><input id=akey readonly value="…"><button onclick="copyKey()">📋</button><button onclick="regenKey()">↻</button></div>
  <span class=meta>Header <code>X-Api-Key</code> oder <code>?apikey=…</code></span>`;
 let k=await(await fetch('/api/apikey')).json();document.getElementById('akey').value=k.apikey||'';}
async function savePrivate(v){
 let r=await(await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({allow_private_webhooks:!!v})})).json();
 document.getElementById('privmsg').textContent=r.ok?t('saved_ok'):t('st_error');}
async function saveVariant(){
 let r=await(await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({variant:readVarPrefs('g')})})).json();
 document.getElementById('vmsg').textContent=r.ok?t('saved_ok'):t('st_error');}
async function regenKey(){if(!confirm('Neuen API-Key erzeugen? Alter wird ungültig. / Regenerate API key?'))return;
 let k=await(await fetch('/api/apikey/regenerate',{method:'POST'})).json();document.getElementById('akey').value=k.apikey||'';}
function copyKey(){let e=document.getElementById('akey');e.select();if(navigator.clipboard)navigator.clipboard.writeText(e.value);}
async function saveGeneral(){let d={general:{app_name:document.getElementById('gname').value.trim(),default_lang:document.getElementById('glang').value,default_design:document.getElementById('gdesign').value}};
 let r=await(await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 document.getElementById('gmsg').textContent=r.ok?t('saved'):t('st_error');}
async function saveQuota(){let d={quota:{enabled:document.getElementById('qen').checked,count:+document.getElementById('qcount').value,days:+document.getElementById('qdays').value}};
 let r=await(await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 document.getElementById('qmsg').textContent=r.ok?t('saved_ok'):t('st_error');}
// Eine Seite je Verfahren (#202). Vorher lagen sieben Verfahren untereinander; wer
// Telegram einrichten wollte, scrollte an Discord vorbei. Die Speicherfunktionen senden
// nur, was auf der Seite steht — der Server fuehrt pro Agent zusammen, deshalb loescht
// eine Teilsendung die anderen NICHT (app.py: `if "telegram" in a` usw.).
async function secNotif(c){
 let s=await(await fetch('/api/settings')).json();
 let dc=s.discord||{},sm=s.smtp||{},ag=s.agents||{};
 let q=x=>(''+(x||'')).replace(/"/g,'&quot;');
 let speichern=(fn,id)=>`<div class=frow><button onclick="${fn}">${t('save')}</button><span id=${id} class=meta></span></div>`;
 let seiten={
  discord:()=>`<h3>${t('notif_discord')}</h3>
   <div class=frow><label style="min-width:auto"><input type=checkbox id=dcen ${dc.enabled?'checked':''}> ${t('active')}</label><span></span></div>
   <div class=frow><input id=dcurl placeholder="${t('webhook_ph')}" value="${q(dc.url)}"><button onclick="testNotify()">${t('test')}</button></div>
   ${speichern('saveSettings()','serr')}`,
  smtp:()=>`<h3>E-Mail (SMTP)</h3>
   <div class=frow><label style="min-width:auto"><input type=checkbox id=smen ${sm.enabled?'checked':''}> ${t('active')}</label><span></span></div>
   <div class=frow><input id=smhost placeholder="Host" value="${q(sm.host)}"><input id=smport placeholder="Port" style="flex:0 0 80px" value="${sm.port||'587'}"></div>
   <div class=frow><input id=smuser placeholder="User" value="${q(sm.user)}"><input id=smpass type=password placeholder="${sm.has_pass?'•••• gesetzt':'Passwort'}"></div>
   <div class=frow><input id=smfrom placeholder="Absender / From" value="${q(sm.from)}"><select id=smtls style="flex:0 0 120px"><option value=starttls ${sm.tls=='starttls'?'selected':''}>STARTTLS</option><option value=ssl ${sm.tls=='ssl'?'selected':''}>SSL</option><option value=none ${sm.tls=='none'?'selected':''}>none</option></select></div>
   <div class=frow><input id=smto placeholder="Test an / to"><button onclick="mailTest()">${t('test')}</button></div>
   ${speichern('saveSmtp()','smmsg')}
   <div class=frow><label style="min-width:auto"><input type=checkbox id=agem ${(ag.email||{}).enabled?'checked':''}> E-Mail bei Verfügbarkeit / email on availability</label><span></span></div>
   ${speichern('saveAgents()','agmsg')}`,
  telegram:()=>`<h3>Telegram</h3>
   <div class=frow><label style="min-width:auto"><input type=checkbox id=agtgen ${(ag.telegram||{}).enabled?'checked':''}> ${t('active')}</label><span></span></div>
   <div class=frow><input id=agtgtok type=password placeholder="${(ag.telegram||{}).has_token?'•••• Token gesetzt':'Bot-Token'}"><input id=agtgchat placeholder="Chat-ID" value="${q((ag.telegram||{}).chat)}"></div>
   ${speichern('saveAgents()','agmsg')}<div class=frow><button onclick="testAgents()" style="background:#2a2f37">${t('test')}</button></div>`,
  webhook:()=>`<h3>Webhook</h3><div class=meta style="margin-bottom:6px">generisch / Slack-kompatibel</div>
   <div class=frow><label style="min-width:auto"><input type=checkbox id=agwhen ${(ag.webhook||{}).enabled?'checked':''}> ${t('active')}</label><span></span></div>
   <div class=frow><input id=agwhurl placeholder="Webhook-URL" value="${q((ag.webhook||{}).url)}"></div>
   ${speichern('saveAgents()','agmsg')}<div class=frow><button onclick="testAgents()" style="background:#2a2f37">${t('test')}</button></div>`,
  gotify:()=>`<h3>Gotify</h3>
   <div class=frow><label style="min-width:auto"><input type=checkbox id=aggoen ${(ag.gotify||{}).enabled?'checked':''}> ${t('active')}</label><span></span></div>
   <div class=frow><input id=aggourl placeholder="Gotify-URL (https://gotify.host)" value="${q((ag.gotify||{}).url)}"><input id=aggotok type=password placeholder="${(ag.gotify||{}).has_token?'•••• App-Token gesetzt':'App-Token'}"></div>
   ${speichern('saveAgents()','agmsg')}<div class=frow><button onclick="testAgents()" style="background:#2a2f37">${t('test')}</button></div>`,
  ntfy:()=>`<h3>ntfy</h3>
   <div class=frow><label style="min-width:auto"><input type=checkbox id=agnten ${(ag.ntfy||{}).enabled?'checked':''}> ${t('active')}</label><span></span></div>
   <div class=frow><input id=agnturl placeholder="ntfy-URL (Standard https://ntfy.sh)" value="${q((ag.ntfy||{}).url)}"><input id=agnttopic placeholder="Topic" style="flex:0 0 160px" value="${q((ag.ntfy||{}).topic)}"><input id=agnttok type=password placeholder="${(ag.ntfy||{}).has_token?'•••• Token':'Token (optional)'}"></div>
   ${speichern('saveAgents()','agmsg')}<div class=frow><button onclick="testAgents()" style="background:#2a2f37">${t('test')}</button></div>`,
  pushover:()=>`<h3>Pushover</h3>
   <div class=frow><label style="min-width:auto"><input type=checkbox id=agpoen ${(ag.pushover||{}).enabled?'checked':''}> ${t('active')}</label><span></span></div>
   <div class=frow><input id=agpouser placeholder="User-Key" value="${q((ag.pushover||{}).user)}"><input id=agpotok type=password placeholder="${(ag.pushover||{}).has_token?'•••• App-Token gesetzt':'App-Token'}"></div>
   ${speichern('saveAgents()','agmsg')}<div class=frow><button onclick="testAgents()" style="background:#2a2f37">${t('test')}</button></div>`,
  maillog:()=>`<h3>${t('notif_maillog')}</h3><div id=mlog class=meta>…</div>`};
 c.innerHTML=(seiten[SETSUB]||seiten.discord)();
 if(SETSUB==='maillog'){
  let ml=await(await fetch('/api/maillog')).json();
  let el=document.getElementById('mlog');if(el)el.innerHTML=ml.length?ml.map(m=>`<div class=frow><span>${m.ok?'🟢':'🔴'} ${m.ts} → ${(''+(m.to||'')).replace(/</g,'&lt;')}</span><span class=meta>${(''+(m.subject||'')).replace(/</g,'&lt;')}${m.err?(' · '+(''+m.err).replace(/</g,'&lt;')):''}</span></div>`).join(''):'—';}}
async function saveSmtp(){let d={smtp:{enabled:document.getElementById('smen').checked,host:document.getElementById('smhost').value,port:document.getElementById('smport').value,user:document.getElementById('smuser').value,from:document.getElementById('smfrom').value,tls:document.getElementById('smtls').value}};
 let pw=document.getElementById('smpass').value;if(pw)d.smtp.pass=pw;
 let r=await(await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 document.getElementById('smmsg').textContent=r.ok?t('saved_ok'):t('st_error');return r.ok;}
async function mailTest(){let to=document.getElementById('smto').value.trim();if(!to)return;await saveSmtp();
 let r=await(await fetch('/api/settings/mail-test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({to:to})})).json();
 document.getElementById('smmsg').textContent=r.ok?t('test_sent'):(r.msg||t('st_error'));}
// Sendet NUR die Verfahren, deren Felder gerade auf der Seite stehen (#202). Der Server
// fuehrt pro Agent zusammen (`if "telegram" in a` …), also bleibt der Rest unangetastet.
// Wuerde hier blind `document.getElementById(...).checked` stehen, riefe die erste
// Unterseite einen TypeError hervor — und eine Sammelsendung mit lauter leeren Feldern
// haette alle anderen Verfahren stillgelegt.
async function saveAgents(){
 let w=id=>document.getElementById(id), a={};
 if(w('agem'))a.email={enabled:w('agem').checked};
 if(w('agtgen')){a.telegram={enabled:w('agtgen').checked,chat:w('agtgchat').value};
  if(w('agtgtok').value)a.telegram.token=w('agtgtok').value;}
 if(w('agwhen'))a.webhook={enabled:w('agwhen').checked,url:w('agwhurl').value};
 if(w('aggoen')){a.gotify={enabled:w('aggoen').checked,url:w('aggourl').value};
  if(w('aggotok').value)a.gotify.token=w('aggotok').value;}
 if(w('agnten')){a.ntfy={enabled:w('agnten').checked,url:w('agnturl').value,topic:w('agnttopic').value};
  if(w('agnttok').value)a.ntfy.token=w('agnttok').value;}
 if(w('agpoen')){a.pushover={enabled:w('agpoen').checked,user:w('agpouser').value};
  if(w('agpotok').value)a.pushover.token=w('agpotok').value;}
 if(!Object.keys(a).length)return true;
 let r=await(await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({agents:a})})).json();
 let m=w('agmsg');if(m)m.textContent=r.ok?t('saved_ok'):t('st_error');
 if(r.ok&&SEK_SUB[SETSEC])subZustand(SETSEC,SEK_SUB[SETSEC]);
 return r.ok;}
async function testAgents(){await saveAgents();
 let r=await(await fetch('/api/settings/notify-test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})})).json();
 document.getElementById('agmsg').textContent=r.ok?t('test_sent'):(r.msg||t('st_error'));}
async function secUsers(c){let list=await(await fetch('/api/users')).json();
 c.innerHTML=`<h3>${t('users')}</h3><div id=ulist></div>
  <h3 style="margin-top:18px">${t('new_user')}</h3>
  <div class=frow><input id=nu placeholder="${t('username')}"><input id=np type=password placeholder="${t('password')}">
   <select id=nr><option value=user>${t('role_user')}</option><option value=admin>${t('role_admin')}</option></select>
   <button onclick="addUser()">${t('create')}</button></div>
  <div id=uerr class=meta style="color:#ff6b6b"></div>`;
 renderUsers(list);}
async function secServices(c){c.innerHTML=`<h3>${t('sec_services')}</h3><button onclick="setSection('services')">${t('refresh')}</button><div id=svc style="margin-top:12px">…</div>`;
 let list=await(await fetch('/api/services/status')).json();
 document.getElementById('svc').innerHTML=list.map(s=>`<div class=frow><span>${s.ok?'🟢':'🔴'} <b>${s.name}</b></span><span class=meta>${(''+ (s.info||'')).replace(/</g,'&lt;')}</span></div>`).join('');}
// Einwurfordner (#416). Der Massenimport lief bisher nur nach Uhr und ueber die API — und
// ein Ordner, in dem Dateien verschwinden oder eben nicht, ohne dass irgendwo steht warum,
// ist genau die Blackbox, die `/api/import/status` verhindern sollte. Die Ansicht zeigt
// deshalb NICHT nur, was einsortiert wird, sondern vor allem, was liegen bleibt und WESHALB.
// --- Bibliothek organisieren (#593) ---
// LESEND. Der Zustand kommt aus <roms>/.umbau/, geschrieben vom laufenden Werkzeug —
// NICHT aus einem Auftragsdatensatz: Romseerr raeumt beim Start laufende Auftraege ab
// (#336), ein Neustart mitten im Umbau wuerde den Eintrag also fuer tot erklaeren,
// waehrend der Umbau weiterlaeuft.
let ORG_TIMER=null;
function orgDauer(s){
 if(s==null)return '–';
 s=Math.max(0,Math.round(s));
 let h=Math.floor(s/3600),m=Math.floor(s%3600/60),k=s%60;
 return h?`${h} h ${m} min`:(m?`${m} min ${k} s`:`${k} s`);}
function orgZahl(n){return (n==null)?'–':n.toLocaleString(LANG||'de');}
function orgStand(art,s){
 let lbl={laeuft:t('org_running'),fertig:t('org_finished'),abgebrochen:t('org_aborted')}[s.zustand]||s.zustand;
 let farbe={laeuft:'#3b82f6',fertig:'#16a34a',abgebrochen:'#d97706'}[s.zustand]||'#888';
 let p=(s.prozent==null)?null:Math.max(0,Math.min(100,s.prozent));
 // Der Balken traegt die Zahl auch als Text: eine Breite allein ist nicht ablesbar,
 // und Screenreader bekommen ueber role=progressbar denselben Wert.
 let balken=(p==null)?'':`<div style="background:#0003;border-radius:6px;height:14px;overflow:hidden;margin:6px 0"
   role=progressbar aria-valuenow="${p}" aria-valuemin="0" aria-valuemax="100"
   aria-label="${lbl}"><div style="width:${p}%;height:100%;background:${farbe}"></div></div>`;
 let zeilen=[
  [t('org_platforms'), `${orgZahl(s.plattformen_erledigt)} / ${orgZahl(s.plattformen_gesamt)}`],
  [t('org_files'), `${orgZahl((s.dateien_gesamt||0)-(s.dateien_offen||0))} / ${orgZahl(s.dateien_gesamt)}`],
  [t('org_elapsed'), orgDauer(s.laeuft_seit)]];
 if(s.zustand==='laeuft'){
  zeilen.push([t('org_remaining'), orgDauer(s.rest_geschaetzt)]);
  if(s.aktuell)zeilen.push([t('org_current'), s.aktuell]);}
 if(s.fehlgeschlagen&&s.fehlgeschlagen.length)
  zeilen.push([t('org_failed'), s.fehlgeschlagen.join(', ')]);
 return `<div class=card style="padding:10px;margin-bottom:10px">
  <div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px">
   <b>${art==='beiwerk'?t('org_beiwerk'):t('org_full')}</b>
   <span style="color:${farbe}">${lbl}${p==null?'':` · ${p} %`}</span></div>
  ${balken}
  <div class=meta>${zeilen.map(z=>`${z[0]}: <b>${z[1]}</b>`).join(' · ')}</div></div>`;}
async function secOrganize(c){
 c.innerHTML=`<h3>${t('sec_organize')}</h3>
  <div class=meta style="line-height:1.6;margin-bottom:8px">${t('org_hint')}</div>
  <div class=meta style="margin-bottom:6px">${t('org_dry_note')} ${t('org_restart_note')}</div>
  <div style="margin:10px 0;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
   <label class=meta>${t('org_platform_l')}
    <input id=orgplat placeholder="${t('org_all')}" style="width:150px" list=orgplats></label>
   <datalist id=orgplats></datalist>
   <label class=meta><input type=checkbox id=orgbeiwerk> ${t('org_beiwerk')}</label>
   <button onclick="orgStart(true)">${t('org_start_dry')}</button>
   <button onclick="orgStart(false)">${t('org_start_real')}</button>
   <button id=orgstop onclick="orgStop()" disabled>${t('org_stop')}</button>
   <button onclick="loadOrganize()">${t('refresh')}</button>
   <span id=orgmsg class=meta></span></div>
  <pre id=orgout class=meta style="display:none;max-height:180px;overflow:auto;white-space:pre-wrap"></pre>
  <div id=orgstand>…</div>
  <h4 style="margin-top:14px">${t('org_logs')}</h4>
  <div id=orglogs class=meta>…</div>`;
 loadOrganize();
 // Vorschlaege aus der Bibliothek — tippen bleibt moeglich, aber der Name muss stimmen,
 // sonst weist der Endpunkt ihn ab.
 fetch('/api/library/platforms').then(r=>r.json()).then(d=>{
  let dl=document.getElementById('orgplats');if(!dl)return;
  let slugs=[];(d.vendors||[]).forEach(v=>(v.systems||[]).forEach(x=>x.slug&&slugs.push(x.slug)));
  dl.innerHTML=slugs.sort().map(x=>`<option value="${x}">`).join('');}).catch(()=>{});}
async function loadOrganize(){
 let d={};try{d=await(await fetch('/api/library/organize/status')).json();}catch(e){d={};}
 let el=document.getElementById('orgstand');if(!el)return;   // Bereich verlassen
 let arten=Object.keys(d.staende||{});
 el.innerHTML = (arten.length ? arten.map(a=>orgStand(a,d.staende[a])).join('')
   : `<div class=meta>${d.vorhanden?t('org_none'):t('org_nodir')}</div>`)
   // Der Hinweis gehoert dorthin, wo die Zahl steht, die er einordnet — also nur,
   // solange ueberhaupt eine Restzeit angezeigt wird.
   + (d.laeuft?`<div class=meta style="margin-bottom:8px">${t('org_est_hint')}</div>`:'');
 let l=document.getElementById('orglogs');
 if(l)l.innerHTML=(d.protokolle&&d.protokolle.length)
   ? d.protokolle.map(e=>`<div style="margin:4px 0">
        <code>${e.name}</code>
        <div class=meta>${t('org_undo')}: <code>${e.zurueck}</code></div></div>`).join('')
   : t('org_nologs');
 // Nur waehrend eines Laufs nachfassen. Ein Dauer-Poll auf einer ruhenden Seite ist
 // Last ohne Auskunft; ausserhalb des Bereichs wird der Zeitgeber abgeraeumt.
 // Anhalten geht NUR fuer einen Lauf aus dieser Instanz — einen, den der
 // Wegwerf-Container gestartet hat, kennt dieser Prozess nicht.
 let stop=document.getElementById('orgstop');
 if(stop)stop.disabled=!d.eigener_lauf;
 let out=document.getElementById('orgout');
 if(out){
  let z=(d.eigener_lauf&&d.eigener_lauf.ausgabe)||[];
  out.style.display=z.length?'block':'none';
  out.textContent=z.join('\n');}
 let m=document.getElementById('orgmsg');
 if(m&&!m.dataset.halten)m.textContent=d.laeuft?(d.eigener_lauf?t('org_own'):t('org_foreign')):'';
 clearTimeout(ORG_TIMER);
 if(d.laeuft&&document.getElementById('orgstand'))ORG_TIMER=setTimeout(loadOrganize,5000);}
async function orgStart(trocken){
 // Nur der ECHTE Lauf fragt nach. Ein Testlauf veraendert nichts, und eine Rueckfrage,
 // die immer kommt, wird weggeklickt, bevor man sie liest.
 if(!trocken&&!confirm(t('org_confirm')))return;
 let plat=(document.getElementById('orgplat').value||'').trim();
 let art=document.getElementById('orgbeiwerk').checked?'beiwerk':'voll';
 let m=document.getElementById('orgmsg');m.dataset.halten='1';m.textContent='…';
 let r={};
 try{r=await(await fetch('/api/library/organize/run',{method:'POST',
   headers:{'Content-Type':'application/json'},
   body:JSON.stringify({art:art,trocken:trocken,plattform:plat})})).json();}catch(e){r={};}
 m.textContent=r.ok?t('org_started'):(r.msg||t('org_failed'));
 delete m.dataset.halten;
 loadOrganize();}
async function orgStop(){
 let m=document.getElementById('orgmsg');m.dataset.halten='1';
 let r={};try{r=await(await fetch('/api/library/organize/stop',{method:'POST'})).json();}catch(e){r={};}
 m.textContent=r.ok?t('org_stopped'):(r.msg||t('org_failed'));
 delete m.dataset.halten;
 loadOrganize();}
async function secDrop(c){
 c.innerHTML=`<h3>${t('sec_drop')}</h3>
  <div class=meta style="line-height:1.6;margin-bottom:8px">${t('drop_hint')}</div>
  <div style="margin:10px 0;display:flex;gap:8px;flex-wrap:wrap;align-items:center">
   <button id=dropbtn onclick="dropScan(this)">${t('drop_scan')}</button>
   <button onclick="loadDrop()">${t('refresh')}</button>
   <span id=dropmsg class=meta></span></div>
  <div id=droplist class=meta>…</div>`;
 loadDrop();}
function dropZeile(sym,datei,text,farbe){
 return `<div class=frow style="gap:8px;align-items:flex-start;padding:3px 0;border-bottom:1px solid #2a2f37">
   <span style="flex:1;min-width:180px">${sym} ${datei.replace(/</g,'&lt;')}</span>
   <span class=meta${farbe?` style="color:${farbe}"`:''}>${(text||'').replace(/</g,'&lt;')}</span></div>`;}
async function loadDrop(){
 let el=document.getElementById('droplist');if(!el)return;
 let d={};try{d=await(await fetch('/api/import/status')).json();}catch(e){el.textContent=t('st_error');return;}
 if(!d.aktiv){
  // Kein Volume: das ist keine Stoerung, sondern eine nicht eingerichtete Funktion. Den
  // erwarteten Pfad MITNENNEN — ohne ihn sucht man das Problem in der falschen Haelfte.
  el.innerHTML=`<div class=meta>⚪ ${t('drop_off')}</div>
   <div class=meta style="margin-top:4px"><code>${(d.pfad||'').replace(/</g,'&lt;')}</code></div>`;
  let b=document.getElementById('dropbtn');if(b)b.disabled=true;
  return;}
 let kopf=`<div class=meta style="margin-bottom:8px"><code>${(d.pfad||'').replace(/</g,'&lt;')}</code>
   · ${t('drop_every').replace('{n}',Math.round((d.takt_sek||300)/60))}</div>`;
 let teile=[];
 let ber=d.bereit||[],off=d.offen||[];
 if(!ber.length&&!off.length)teile.push(`<div class=meta>${t('drop_none')}</div>`);
 if(ber.length)teile.push(`<div style="margin-top:6px"><b>${t('drop_ready')}</b> (${d.bereit_gesamt||ber.length})</div>`
  +ber.map(x=>dropZeile('→',x.datei,x.slug+' · '+(x.grund||''))).join('')
  +((d.bereit_gesamt||0)>ber.length?`<div class=meta>${t('drop_more').replace('{n}',(d.bereit_gesamt-ber.length))}</div>`:''));
 if(off.length)teile.push(`<div style="margin-top:10px"><b>${t('drop_stuck')}</b> (${d.offen_gesamt||off.length})</div>`
  +off.map(x=>dropZeile('•',x.datei,x.grund,'#d29922')).join('')
  +((d.offen_gesamt||0)>off.length?`<div class=meta>${t('drop_more').replace('{n}',(d.offen_gesamt-off.length))}</div>`:''));
 el.innerHTML=kopf+teile.join('');}
async function dropScan(btn){
 let m=document.getElementById('dropmsg');if(m)m.textContent=t('drop_running');
 if(btn)btn.disabled=true;
 let d={};try{d=await(await fetch('/api/import/scan',{method:'POST'})).json();}catch(e){d={};}
 if(btn)btn.disabled=false;
 if(m)m.textContent=d.ok?t('drop_done').replace('{a}',d.eingeordnet||0).replace('{o}',d.offen||0):t('st_error');
 loadDrop();}
async function secAbout(c){
 let st={};try{st=await(await fetch('/api/admin/stats')).json();}catch(e){}
 let ver={};try{ver=await(await fetch('/api/version?check=1')).json();}catch(e){}
 let repo='https://github.com/Sparxx947/romseerr';
 let build=[ver.commit?ver.commit.slice(0,7):'',ver.built_at||''].filter(Boolean).join(' · ');
 // DER LINK MUSS DORTHIN FUEHREN, WOHIN SEIN TEXT ZEIGT. `/releases/latest` ist dieselbe
 // Falle wie der gleichnamige API-Endpunkt aus #572: Es ueberspringt Vorabversionen. An
 // fremden Repos nachgemessen — kubernetes/kubernetes leitet auf v1.36.3 um, obwohl
 // v1.37.0-rc.0 neuer ist, und ohne infrage kommenden Release landet man auf der Uebersicht
 // /releases. Da hier alle Releases Betas sind, nannte der Text die eine Version und der
 // Klick fuehrte zu einer anderen. `ver.latest` kommt ohne fuehrendes v (der Server
 // schneidet es ab), das Tag traegt es — wie in der Fusszeile. (#577)
 let updUrl=ver.latest?`${repo}/releases/tag/v${encodeURIComponent(ver.latest)}`:`${repo}/releases`;
 let upd=ver.update_available?` <a href="${updUrl}" target=_blank rel="noopener noreferrer" style="color:#5b8cff">${t('upd_avail')} ${ver.latest}</a>`
        :(ver.latest?` <span style="color:#3fb950">${t('upd_current')}</span>`:'');
 c.innerHTML=`<h3>🎮 Romseerr — ${t('sec_about')}</h3>
  <p class=meta style="margin:2px 0 12px">${t('about_txt')}</p>
  <div class=frow><span style="min-width:150px">${t('version')}</span><span class=meta>${ver.version||window.VERSION||'—'}${upd}</span></div>
  ${build?`<div class=frow><span style="min-width:150px">${t('about_build')}</span><span class=meta>${build}</span></div>`:''}
  ${ver.provenance&&ver.provenance!=='build'?`<div class=frow><span style="min-width:150px"></span>
    <span class=meta style="color:#d29922">⚠ ${t('about_no_build')}</span></div>`:''}
  <div class=frow><span style="min-width:150px">${t('about_lib')}</span><span class=meta>${(st.lib_titles||0).toLocaleString()} ${t('about_titles')} · ${st.lib_platforms||0} ${t('about_platforms')}</span></div>
  <div class=frow><span style="min-width:150px">${t('about_jobs')}</span><span class=meta>${st.jobs_total||0} (${st.jobs_active||0} ${t('about_active')})</span></div>
  <h3 style="font-size:13px;margin-top:16px">${t('about_links')}</h3>
  <div class=meta style="line-height:1.9">
   🔗 <a href="${repo}" target=_blank rel="noopener noreferrer" style="color:#5b8cff">GitHub-Repo</a><br>
   📖 <a href="${repo}/wiki" target=_blank rel="noopener noreferrer" style="color:#5b8cff">Wiki</a> · <a href="/api/docs" target=_blank rel="noopener noreferrer" style="color:#5b8cff">API-Doku</a> · <a href="${repo}/blob/main/CHANGELOG.md" target=_blank rel="noopener noreferrer" style="color:#5b8cff">Changelog</a><br>
   🐞 <a href="${repo}/issues" target=_blank rel="noopener noreferrer" style="color:#5b8cff">Issues melden</a> · 🔒 <a href="${repo}/security/advisories/new" target=_blank rel="noopener noreferrer" style="color:#5b8cff">Sicherheitslücke melden</a>
  </div>
  <h3 style="font-size:13px;margin-top:16px">${t('about_feat')}</h3>
  <div class=meta style="line-height:1.7">${t('about_feat_txt')}</div>
  <h3 style="font-size:13px;margin-top:16px">${t('about_stack')}</h3>
  <div class=meta style="line-height:1.7">${t('about_stack_txt')}</div>
  <p class=meta style="margin-top:16px">${t('about_license')} · <button onclick="startWizard()" style="background:#2a2f37;border:none;color:#e6e8ec;padding:5px 10px;border-radius:6px;cursor:pointer">${t('wiz_reopen')}</button></p>`;}
async function secBlocklist(c){let list=await(await fetch('/api/blocklist')).json();
 // Am Code nachgelesen, nicht vermutet (#203): `is_blocked` prüft `p in t` über
 // kleingeschriebene Zeichenketten — also Teilstring, keine Regex, ohne Rücksicht auf
 // Groß-/Kleinschreibung, und ausschließlich gegen den TITEL. Aufgerufen wird sie in der
 // Suche, in den Entdecken-Reihen, bei den Empfehlungen und in `api_download` — dort
 // lehnt sie eine neue Anfrage ab. Laufende Aufträge sieht sie nie.
 c.innerHTML=`<h3>${t('blocklist')}</h3>
  <div class=meta style="margin:2px 0 12px;line-height:1.7;max-width:70ch">${t('bl_hint')}</div>
  <div id=bllist></div>
  <div class=frow><input id=blnew placeholder="${t('pattern_ph')}"><button onclick="blAdd()">${t('add_btn')}</button></div>`;
 renderBlock(list);}
function renderBlock(list){window.BL=list.slice();let d=document.getElementById('bllist');d.innerHTML='';
 list.forEach((p,i)=>{let row=document.createElement('div');row.className='frow';
  let s=document.createElement('span');s.textContent='🚫 '+p;row.appendChild(s);
  let b=document.createElement('button');b.textContent=t('del');b.onclick=()=>{window.BL.splice(i,1);blSave();};
  row.appendChild(b);d.appendChild(row);});}
async function blSave(){let r=await(await fetch('/api/blocklist',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({patterns:window.BL})})).json();
 if(r.ok)setSection('blocklist');}
function blAdd(){let v=document.getElementById('blnew').value.trim();if(!v)return;window.BL=(window.BL||[]).concat([v]);blSave();}
async function saveSettings(){let d={discord:{enabled:document.getElementById('dcen').checked,url:document.getElementById('dcurl').value.trim()}};
 let r=await(await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 document.getElementById('serr').textContent=r.ok?t('saved'):t('st_error');}
async function testNotify(){let d={discord:{url:document.getElementById('dcurl').value.trim()}};
 let r=await(await fetch('/api/settings/notify-test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 document.getElementById('serr').textContent=r.ok?t('test_sent'):(r.msg||t('st_error'));}
async function approveJob(id){await fetch('/api/jobs/'+id+'/approve',{method:'POST'});loadJobs();}
async function denyJob(id){await fetch('/api/jobs/'+id+'/deny',{method:'POST'});loadJobs();}
async function retryJob(id){
 let r={};try{r=await(await fetch('/api/jobs/'+id+'/retry',{method:'POST'})).json();}catch(e){}
 // Ohne diese Meldung sähe „alle Quellen erschöpft" wie ein wirkungsloser Knopf aus. (#200)
 if(r&&r.exhausted)alert(t('exhausted')+(r.tried&&r.tried.length?' ('+r.tried.join(', ')+')':''));
 loadJobs();updateJobBadge();}
// Anfrage entfernen. Liegen noch Dateien, MUSS die Entscheidung darüber hier fallen: der
// Auftrag ist das Einzige, was den Ordner noch einem Titel zuordnet. (#246)
async function deleteJob(id,hatDateien){
 let files=false;
 if(hatDateien){
  if(!confirm(t('del_withfiles')))files=false; else files=true;
 }else if(!confirm(t('del_confirm')))return;
 let r={};try{r=await(await fetch('/api/jobs/'+id,{method:'DELETE',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({files:files})})).json();}catch(e){}
 if(r&&r.files_left)alert(t('del_left'));   // muss auffallen: es bleiben Daten liegen
 loadJobs();updateJobBadge();}
// Erneut einlesen statt neu herunterladen: die Daten liegen schon da. (#245)
async function reimportJob(id){
 let r={};try{r=await(await fetch('/api/jobs/'+id+'/reimport',{method:'POST'})).json();}catch(e){}
 if(r&&r.ok===false)alert(r.msg||t('reimp_gone'));
 setTimeout(loadJobs,600);}
async function openUsers(){let m=document.getElementById('modal');m.style.display='block';
 let list=await(await fetch('/api/users')).json();
 let inp='style="flex:1;min-width:90px;background:#0b0d10;border:1px solid #2c323b;color:#e6e8ec;padding:8px;border-radius:6px"';
 m.innerHTML=`<div class=box><button class=x onclick="closeModal()">×</button>
  <div class=sec><h3>${t('users')}</h3><div id=ulist></div></div>
  <div class=sec><h3>${t('new_user')}</h3>
   <div class=row><input id=nu placeholder="${t('username')}" ${inp}>
    <input id=np type=password placeholder="${t('password')}" ${inp}>
    <select id=nr ${inp}><option value=user>${t('role_user')}</option><option value=admin>${t('role_admin')}</option></select>
    <label style="font-size:12px;color:#8b929e;display:flex;gap:5px;align-items:center"><input type=checkbox id=naa> ${t('autoapprove')}</label>
    <button onclick="addUser()">${t('create')}</button></div>
   <div id=uerr style="color:#ff6b6b;font-size:12px;margin-top:6px"></div></div></div>`;
 renderUsers(list);}
const PERM_KEYS=['request','autoapprove','manage_requests','manage_users','manage_issues','manage_settings','quota_exempt'];
const PERM_LBL={request:'Anfragen',autoapprove:'Auto-Freigabe',manage_requests:'Anfr. verwalten',manage_users:'Benutzer',manage_issues:'Probleme',manage_settings:'Einstellungen',quota_exempt:'kein Limit'};
function renderUsers(list){let ul=document.getElementById('ulist');ul.innerHTML='';
 list.forEach(u=>{let row=document.createElement('div');row.style.cssText='background:#171a20;border-radius:8px;padding:10px;margin-bottom:8px';
  let head=document.createElement('div');head.style.cssText='display:flex;justify-content:space-between;align-items:center';
  head.innerHTML=`<b>${u.role=='admin'?'👑 ':'👤 '}${(''+u.username).replace(/</g,'&lt;')}</b>`;
  let del=document.createElement('button');del.textContent=t('del');del.style.cssText='background:#6e2a2a;border:none;color:#fff;padding:4px 10px;border-radius:6px;cursor:pointer';
  del.onclick=async()=>{let d=await(await fetch('/api/users/'+encodeURIComponent(u.username),{method:'DELETE'})).json();if(d.ok)setSection('users');else alert(d.msg||'Fehler');};
  head.appendChild(del);row.appendChild(head);
  if(u.role=='admin'){let a=document.createElement('div');a.className='meta';a.style.marginTop='6px';a.textContent='alle Rechte / all permissions';row.appendChild(a);}
  else{let pg=document.createElement('div');pg.style.cssText='display:flex;flex-wrap:wrap;gap:10px;margin-top:8px';
   PERM_KEYS.forEach(pk=>{let lbl=document.createElement('label');lbl.style.cssText='font-size:11px;color:#8b929e;display:flex;gap:4px;align-items:center';
    let cb=document.createElement('input');cb.type='checkbox';cb.checked=(u.perms||[]).includes(pk);
    cb.onchange=()=>{let np=(u.perms||[]).filter(x=>x!=pk);if(cb.checked)np.push(pk);u.perms=np;
     fetch('/api/users/'+encodeURIComponent(u.username),{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({perms:np})});};
    lbl.appendChild(cb);lbl.appendChild(document.createTextNode(PERM_LBL[pk]));pg.appendChild(lbl);});
   row.appendChild(pg);}
  ul.appendChild(row);});}
async function addUser(){let u=document.getElementById('nu').value.trim(),p=document.getElementById('np').value,r=document.getElementById('nr').value;
 let d=await(await fetch('/api/users',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({username:u,password:p,role:r})})).json();
 if(d.ok)setSection('users');else document.getElementById('uerr').textContent=d.msg||'Fehler';}
async function logout(){await fetch('/api/logout',{method:'POST'});location.href='/login';}
// Beim Start dasselbe: erst die Sprache, dann zeichnen. Bei Deutsch — dem Normalfall und
// der Vorgabe — ist `i18nLaden` sofort fertig, es entsteht also keine Verzoegerung.
// Alles Weitere wartet mit, damit kein Teil der Seite in einer anderen Sprache erscheint
// als der Rest. / Everything waits together, or parts of the page would render in
// different languages.
i18nLaden(LANG).then(()=>{
 applyI18n();zeichneKopf();loadAuth();loadPlatforms();loadDiscover();updateMsgBadge();
// Adresse zuerst auswerten: sonst landet ein Neuladen immer auf Entdecken, egal was in
// der Adresszeile steht. replaceState, damit vor der Startansicht kein leerer Eintrag
// im Verlauf liegt. (#194)
// ERST parsen, DANN normalisieren: routeSetzen schreibt die Adresse, und wer sie
// vorher liest, liest seine eigene Ausgabe. Genau so ging beim Start die Unterseite
// verloren — `#/settings/notif/telegram` landete auf `#/settings/general`. (#194/#202)
{let r0=routeParse(location.hash);
 routeSetzen(r0.view,r0.detail,true,r0.sec,r0.sub);
 routeAnwenden();}
if('serviceWorker'in navigator){navigator.serviceWorker.register('/sw.js').catch(()=>{});}
document.getElementById('q').addEventListener('keydown',e=>{if(e.key=='Enter')search();});
setInterval(()=>{if(cur=='j')loadJobs();},4000);
// Der Zähler ist nur nützlich, wenn er sich von selbst bewegt — sonst müsste man die
// Seite öffnen, um zu erfahren, ob man sie öffnen muss. (#198)
setInterval(updateJobBadge,15000);
});   // Ende von i18nLaden(LANG).then — der gesamte Start haengt daran (#350)
