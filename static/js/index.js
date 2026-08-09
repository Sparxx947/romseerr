const I18N={de:{
 nav_discover:'🔍 Entdecken',nav_requests:'📥 Anfragen',nav_users:'👤 Benutzer',nav_settings:'⚙️ Einstellungen',logout:'🚪 Abmelden',
 search_ph:'Spiel suchen … (Enter)',platforms:'Plattformen',all:'Alle',selected:'gewählt',
 hint_type:'Tippe einen Titel und drücke Enter.',loading_home:'Lade Startseite …',popular_on:'Beliebt auf',click_search:'klick zum Suchen',
 searching:'Suche läuft …',no_results:'Keine Treffer.',results:'Treffer',in_library:'✓ in Bibliothek',download:'⬇ Download',requested:'✓ angefragt',collection:'Sammlung',
 versions:'Versionen / Quellen',files:'Dateien',no_desc:'Keine Beschreibung verfügbar.',screenshots:'Screenshots',similar:'Ähnliche Spiele',series:'Reihe',because_you:'Weil du angefragt hast:',
 no_requests:'Noch keine Anfragen.',approve:'Freigeben',deny:'Ablehnen',retry:'Erneut',reset:'Alle zurücksetzen',req_all:'Alle anfragen',flt_user:'Nutzer',flt_all:'Alle',wishlist:'Wunschliste',nav_coverage:'Abdeckung',emu_install:'installieren',emu_needs_url:'Für diesen Emulator gibt es keine automatisch ermittelbare Quelle — URL in der .env des Streaming-Hosts eintragen.',emu_needs_url_kurz:'URL nötig',emu_rb_confirm:'{n} auf die vorherige Fassung zurücksetzen?',emu_rb_failed:'Zurücksetzen fehlgeschlagen',emu_update:'Emulatoren aktualisieren',emu_nohost:'kein Streaming-Host erreichbar',emu_nolauncher:'kein Start-Dienst hinterlegt',emu_unreachable:'Start-Dienst nicht erreichbar',emu_running:'Aktualisierung läuft …',emu_none:'keine Emulatoren installiert',emu_ok:'zuletzt erfolgreich',emu_failed:'zuletzt fehlgeschlagen',fw_hint:'BIOS und Firmware liegen auf dem Streaming-Host, nicht in Romseerr. Was hier fehlt, endet im Stream als schwarzes Bild — deshalb steht es je Plattform.',fw_ready:'vollständig',fw_notinstalled:'Datei liegt bereit, ist im Emulator aber nicht eingespielt — einmalig dort installieren',fw_missing:'fehlt',fw_badsize:'Größe unerwartet — abgebrochener Download?',fw_upload:'Datei hochladen',fw_vendor:'beim Hersteller holen',fw_docs:'Anleitung',fw_nolauncher:'kein Start-Dienst hinterlegt — Firmware-Stand unbekannt',fw_fetching:'Hersteller-Download läuft …',fw_sending:'übertrage',fw_failed:'Übertragung fehlgeschlagen',stream:'Streamen',stream_single:'Einzelplatz — eine Sitzung gleichzeitig',stream_busy:'Belegt: {u} spielt gerade {g}',stream_stop:'Sitzung beenden',stream_not_in_lib:'Zum Streamen muss der Titel in der Bibliothek liegen.',stream_no:'Streamen gerade nicht möglich.',stream_running:'▶ läuft — Fenster geöffnet',stream_manual:'Desktop geöffnet — Titel dort starten',stream_failed:'Start fehlgeschlagen — Desktop geöffnet',stream_title:'Streaming-Host',stream_hint:'Für Plattformen, die der Browser nicht emulieren kann (PS2, GameCube, Wii, Switch). Der Emulator läuft auf dem Host, der Browser bekommt Bild und Ton. Ohne Start-Dienst öffnet Romseerr nur den Desktop.',stream_url_l:'Browser-URL des Hosts',stream_launch_l:'Start-Dienst (optional)',sec_outbound:'Ausgehende Anfragen',outbound_hint:'Webhook- und Katalog-URLs setzt der Nutzer. Standardmäßig lehnt Romseerr Ziele im privaten Netz, auf Loopback und Link-Local ab — sonst könnte jeder angemeldete Nutzer den Server auf interne Adressen schicken. Wer sein Benachrichtigungsziel im selben Netz betreibt, muss das hier ausdrücklich erlauben.',outbound_allow:'Ziele im privaten Netz erlauben',play:'Im Browser spielen',play_no_romm:'Spielen nicht möglich — RomM ist nicht verbunden.',play_no_core:'Diese Plattform lässt sich im Browser nicht emulieren.',play_not_in_lib:'Zum Spielen muss der Titel in der Bibliothek liegen.',play_too_large:'Zu groß für den Browser (Grenze {mb} MB).',play_no_title:'Kein Titel.',play_bios:'braucht BIOS',play_romset:'Arcade: nur mit passendem Romset',cat_title:'Filehoster-Kataloge (experimentell)',cat_hint:'Katalog-JSON-Quellen, eine URL je Zeile. Bewusst NICHT mitgeliefert — die Quellen bestimmt der Betreiber. Format: {name, downloads:[{title,uris,uploadDate,fileSize}]}.',cat_urls:'Quell-URLs',cat_refresh:'Jetzt holen',cat_none:'keine Quelle hinterlegt — der Filehoster-Weg ist inaktiv',cat_items:'Einträge insgesamt',cfg_warn:'Konfiguration',cfg_warn_hint:'Ein Weg ist nicht benutzbar — Downloads darüber starten gar nicht erst.',notif_maillog:'Mail-Protokoll',conn_scraper:'Scraper / Cover-Quellen',sub_an:'aktiv',sub_da:'eingerichtet, aber aus',sub_leer:'nicht eingerichtet',details:'Details',nav_lists:'Meine Listen',favourites:'Favoriten',favourite:'Favorit',fav_empty:'Noch keine Favoriten.',fav_remove:'Entfernen',fav_hint:'Titel, die du schnell wiederfinden willst. Anders als die Wunschliste verschwinden sie nie von selbst.',wl_hint_head:'Wunschliste — was du noch nicht hast',flt_active:'aktiv',flt_done:'erledigt',flt_failed:'fehlgeschlagen',flt_leer:'In diesem Filter ist nichts.',flt_denied:'abgelehnt',cov_measurable:'{n} von {m} Konsolen messbar',cov_method:'Summe besessen ÷ Summe bekannt — nicht das Mittel der Prozente, das gäbe kleinen Systemen dasselbe Gewicht wie großen.',bl_hint:'<b>Teilstring, keine Regex.</b> Ein Eintrag greift, wenn er irgendwo im <b>Titel</b> vorkommt — Groß-/Kleinschreibung egal, Sonderzeichen wie <code>.</code> oder <code>*</code> stehen für sich selbst. Geprüft wird <b>nur der Titel</b>, nicht Dateiname, Release-Gruppe oder Plattform. Die Regel wirkt in Suche, Entdecken und Empfehlungen und <b>lehnt neue Anfragen ab</b>. Einen <b>bereits laufenden Auftrag hält sie nicht an</b>, und schon vorhandene Dateien entfernt sie nicht. Sie gilt für <b>alle Nutzer</b> dieser Instanz.',rate_title:'Bewertung',rate_mine:'deine Bewertung',rate_others:'andere',rate_clear:'zurücknehmen',comments:'Kommentare',comments_none:'Noch keine Kommentare.',jd_hint:'Drei Sichten auf dieselbe Übergabe: die ersten beiden sieht Romseerr, die dritte JDownloader. Leer = Standard.',jd_watch:'Watch-Ordner (Romseerr schreibt)',jd_out:'Fertig-Ordner (Romseerr liest)',jd_base:'Download-Basis (JDownloader-Sicht)',var_prefs:'Fassungen (Region/Sprache)',var_region_order:'Regionsreihenfolge — die Reihenfolge ist die Vorliebe',var_lang:'Bevorzugte Sprache',var_prerelease:'Beta/Prototyp/Demo zulassen',var_unspec:'unspezifiziert',var_preferred:'bevorzugt',var_hint:'Instanzweiter Rückfall für Nutzer, die selbst nichts eingestellt haben. Region ändert Inhalt (Sprache, Schwierigkeit, Zensur, 50/60 Hz) — das ist keine Qualitätsleiter, deshalb wird nach dieser Reihenfolge gewählt und nicht sortiert.',var_of:'Fassung',ra_achievements:'Achievements',ra_points:'Punkte',ra_earned:'erreicht',ra_user:'RetroAchievements-Konto (optional)',ra_refresh:'Sets holen',ra_sets:'Sets',ra_nokey:'kein API-Key hinterlegt',ra_unmapped:'ohne Konsolen-Zuordnung',ra_only:'nur mit Achievements',cov_of:'von',cov_src:'Quelle',cov_asof:'Stand',cov_files:'Dateien',cov_missing:'fehlende Titel',cov_refresh:'Katalog aktualisieren',cov_nosnap:'keine Momentaufnahme — Katalog noch nicht geholt',cov_nosource:'keine Katalogquelle für diese Plattform',cov_basis:'Grundlage ist eine Momentaufnahme aus {src} (max. {max} Titel je Plattform). Metadatensätze sind sich uneins, was als eigener Titel zählt — die Prozentzahl ist eine Orientierung, kein Messwert.',cov_search:'Suchen',cov_none:'Nichts fehlt (oder kein Katalog).',cov_filter:'Filtern …',cov_filter_do:'Filtern',cov_wish_sel:'Auswahl auf die Wunschliste',wl_import:'Import',wl_imp_hint:'Liste einfügen oder Datei wählen (TXT/CSV) — ein Titel je Zeile, optional Titel;Plattform. Nichts wird geschrieben, bevor du die Vorschau bestätigst.',wl_imp_example:'Beispieldatei herunterladen',wl_imp_ph:'Chrono Trigger\nSuper Metroid;snes',wl_imp_preview:'Vorschau',wl_imp_apply:'Übernehmen',wl_imp_none:'Nichts ausgewählt.',wl_imp_done:'{a} übernommen, {s} übersprungen.',wl_imp_trunc:'Nur die ersten {n} Zeilen werden geprüft.',wl_imp_toobig:'Datei zu groß (max. 200 kB).',wl_imp_nocheck:'Ohne IGDB-Zugang kein Katalogabgleich — Einträge werden ungeprüft übernommen.',wl_s_matched:'getroffen',wl_s_ambiguous:'mehrdeutig',wl_s_notfound:'nicht gefunden',wl_s_duplicate:'schon gemerkt',wl_s_inlib:'schon vorhanden',wl_s_unverified:'ungeprüft',add_wishlist:'⭐ Merken',wl_added:'⭐ gemerkt',wl_empty:'Wunschliste leer.',wl_remove:'Entfernen',
 users:'Benutzer',new_user:'Neuen Benutzer anlegen',create:'Anlegen',del:'Löschen',autoapprove:'Auto-Freigabe',role_user:'Nutzer',role_admin:'Admin',username:'Benutzername',password:'Passwort',
 notif_discord:'Benachrichtigungen — Discord',active:'aktiv',test:'Test',save:'Speichern',saved:'gespeichert ✓',test_sent:'Test gesendet ✓',webhook_ph:'Discord Webhook-URL',
 st_pending:'⏳ Wartet auf Freigabe',st_queued:'Angefragt',st_downloading:'Lädt…',st_importing:'Wird verarbeitet',st_done:'✅ Verfügbar',st_error:'Fehler',st_denied:'Abgelehnt',st_exists:'vorhanden',
 settings:'Einstellungen',sec_general:'Allgemein',sec_notif:'Benachrichtigungen',sec_users:'Benutzer',sec_services:'Dienste',sec_about:'Über',app_name:'App-Name',default_lang:'Standardsprache',refresh:'Aktualisieren',version:'Version',about_build:'Build',about_no_build:'Herkunft unbekannt — diese Instanz kann nicht sagen, ob sie dem Quellstand entspricht.',upd_avail:'Update verfügbar:',upd_current:'aktuell',about_txt:'Selbstgebauter Seerr-Klon für ROMs.',wiz_welcome:'Willkommen bei Romseerr',wiz_welcome_txt:'Dieser Assistent verbindet dich Schritt für Schritt mit den Diensten des Stacks (SABnzbd, Prowlarr, IGDB, RomM). Jeden Schritt kannst du testen oder überspringen.',wiz_done:'Fertig!',wiz_done_txt:'Die Grundkonfiguration steht. Alles lässt sich später unter Einstellungen → Verbindungen anpassen.',wiz_next:'Weiter',wiz_back:'Zurück',wiz_skip:'Überspringen',wiz_finish:'Loslegen',wiz_step:'Schritt',wiz_reopen:'Assistent erneut öffnen',about_lib:'Bibliothek',about_titles:'Titel',about_platforms:'Plattformen',about_jobs:'Anfragen',about_active:'aktiv',about_links:'Links',about_feat:'Funktionen',about_feat_txt:'Suche über Archive.org + Usenet, Dedup, Discover, Anfragen mit Freigabe, Benutzer & Rechte, Kontingente, Benachrichtigungen (Discord/Telegram/E-Mail/Web-Push), Probleme, PWA, API.',about_stack:'Stack',about_stack_txt:'Orchestriert Prowlarr, SABnzbd, JDownloader und RomM. Verbindungen in den Einstellungen konfigurierbar.',about_license:'Lizenz: MIT',sec_maint:'Logs & Wartung',exp_title:'Export / Import',exp_hint:'Sichert Einstellungen, Benutzer & Rechte, Anfragen und Wunschlisten als JSON. Ohne Passphrase bleiben Geheimnisse (Kennwörter, API-Keys, Webhook-URLs) AUSSEN VOR — mit Passphrase werden sie verschlüsselt beigelegt. Dieselbe Passphrase wird beim Import gebraucht.',exp_pass:'Passphrase',exp_pass_ph:'leer = ohne Geheimnisse',exp_do:'Exportieren',exp_merge:'Zusammenführen',exp_replace:'Ersetzen',imp_do:'Importieren',exp_done_plain:'Exportiert (ohne Geheimnisse).',exp_done_enc:'Exportiert (Geheimnisse verschlüsselt).',imp_nofile:'Keine Datei gewählt.',imp_badjson:'Datei ist kein gültiges JSON.',imp_conf_merge:'Import zusammenführen? Bestehende Werte werden überschrieben, nicht genannte bleiben.',imp_conf_replace:'ERSETZEN? Benutzer, Anfragen und Wunschlisten werden vollständig durch die Datei ersetzt.',imp_done:'Importiert:',logs:'Protokoll',clear_cache:'Cache leeren',reindex:'Neu indexieren',clear_finished:'Fertige entfernen',done_word:'Erledigt',lbl_jobs:'Anfragen',lbl_lib:'Bibliothek',sec_conn:'Verbindungen',reveal:'Klartext anzeigen',tls_hint:'Cert + Schlüssel (PEM) hinterlegen — die App startet dann zusätzlich einen HTTPS-Listener auf dem gewählten Port (Neustart nötig). Für Web-Push/PWA ohne separaten Reverse-Proxy.',tls_none:'kein Zertifikat hinterlegt',tls_expires:'gültig bis',tls_key_note:'privater Schlüssel — wird nie angezeigt',tls_restart:'Container neu starten zum Aktivieren',conn_hint:'Leere Felder nutzen den Wert aus der Umgebung (.env). Secrets sind maskiert — leer lassen behält den bestehenden Wert.',un_check:'Usenet-Weg prüfen',un_hint:'Misst die Kette Suche → Kategorie → Warteschlange → Einsammelordner, ohne etwas herunterzuladen. Die letzte Zeile zeigt beide Sichten auf denselben Ordner — laufen sie auseinander, läuft der Download durch und wird trotzdem nie gefunden.',un_search:'Suche über Prowlarr',un_cat:'SAB-Kategorie',un_queue:'Warteschlange',un_collect:'Einsammelordner',
 profile:'Profil',display_name:'Anzeigename',email:'E-Mail',language:'Sprache',design:'Design',default_design:'Standard-Design',d_seerr:'Seerr',d_glass:'Glas',d_clean:'Klar',avatar:'Avatar',pwebhook:'Persönlicher Discord-Webhook',change_pw:'Passwort ändern',cur_pw:'Aktuelles Passwort',new_pw:'Neues Passwort',choose_img:'Bild wählen',saved_ok:'gespeichert ✓',
 blocklist:'Sperrliste',add_btn:'Hinzufügen',pattern_ph:'Stichwort/Muster im Titel',
 nav_issues:'🐞 Probleme',nav_messages:'Nachrichten',msg_to:'An',msg_none:'Noch keine Nachrichten.',msg_ph:'Nachricht schreiben …',msg_send:'Senden',msg_hint:'Strg+Enter sendet',msg_nousers:'Keine anderen Benutzer.',req_for:'Anfrage für',req_self:'mich selbst',issues:'Probleme',report_issue:'Problem melden',issue_msg:'Beschreibung',close_btn:'Schließen',st_open:'offen',st_closed:'geschlossen',submit:'Absenden',issue_type:'Art',comment_ph:'Kommentar schreiben …',comment_send:'Senden',push_enable:'🔔 Push aktivieren',push_disable:'🔕 Push deaktivieren',push_unsupported:'Push nicht verfügbar (HTTPS nötig)',push_denied:'Erlaubnis verweigert',push_on:'Push aktiviert ✓',push_off:'Push deaktiviert'
},en:{
 nav_discover:'🔍 Discover',nav_requests:'📥 Requests',nav_users:'👤 Users',nav_settings:'⚙️ Settings',logout:'🚪 Sign out',
 search_ph:'Search a game … (Enter)',platforms:'Platforms',all:'All',selected:'selected',
 hint_type:'Type a title and press Enter.',loading_home:'Loading home …',popular_on:'Popular on',click_search:'click to search',
 searching:'Searching …',no_results:'No results.',results:'results',in_library:'✓ in library',download:'⬇ Download',requested:'✓ requested',collection:'Collection',
 versions:'Versions / sources',files:'Files',no_desc:'No description available.',screenshots:'Screenshots',similar:'Similar games',series:'Series',because_you:'Because you requested:',
 no_requests:'No requests yet.',approve:'Approve',deny:'Deny',retry:'Retry',reset:'Reset all',req_all:'Request all',flt_user:'User',flt_all:'All',wishlist:'Wishlist',nav_coverage:'Coverage',emu_install:'install',emu_needs_url:'No automatically resolvable source for this emulator — set its URL in the streaming host .env.',emu_needs_url_kurz:'URL required',emu_rb_confirm:'Roll {n} back to the previous build?',emu_rb_failed:'rollback failed',emu_update:'Update emulators',emu_nohost:'no streaming host reachable',emu_nolauncher:'no launch service configured',emu_unreachable:'launch service unreachable',emu_running:'update running …',emu_none:'no emulators installed',emu_ok:'last run succeeded',emu_failed:'last run failed',fw_hint:'BIOS and firmware live on the streaming host, not in Romseerr. Anything missing here shows up as a black screen in the stream, so it is listed per platform.',fw_ready:'complete',fw_notinstalled:'file is present but not installed in the emulator — install it there once',fw_missing:'missing',fw_badsize:'unexpected size — truncated download?',fw_upload:'upload file',fw_vendor:'fetch from vendor',fw_docs:'docs',fw_nolauncher:'no launch service configured — firmware state unknown',fw_fetching:'vendor download running …',fw_sending:'uploading',fw_failed:'upload failed',stream:'Stream',stream_single:'single seat — one session at a time',stream_busy:'In use: {u} is playing {g}',stream_stop:'End session',stream_not_in_lib:'The title must be in the library to stream it.',stream_no:'Streaming not available right now.',stream_running:'▶ running — window opened',stream_manual:'desktop opened — start the title there',stream_failed:'launch failed — desktop opened',stream_title:'Streaming host',stream_hint:'For platforms the browser cannot emulate (PS2, GameCube, Wii, Switch). The emulator runs on the host; the browser receives video and audio. Without a launch service Romseerr only opens the desktop.',stream_url_l:'Browser URL of the host',stream_launch_l:'Launch service (optional)',sec_outbound:'Outbound requests',outbound_hint:'Webhook and catalogue URLs come from users. By default Romseerr refuses private, loopback and link-local targets — otherwise any logged-in user could point the server at internal addresses. If your notification target lives on the same network, allow it explicitly here.',outbound_allow:'Allow targets in private networks',play:'Play in browser',play_no_romm:'Cannot play — RomM is not connected.',play_no_core:'This platform cannot be emulated in the browser.',play_not_in_lib:'The title must be in the library to play it.',play_too_large:'Too large for the browser (limit {mb} MB).',play_no_title:'No title.',play_bios:'needs BIOS',play_romset:'arcade: only with a matching romset',cat_title:'Filehoster catalogues (experimental)',cat_hint:'Catalogue JSON sources, one URL per line. Deliberately not shipped — the operator supplies the sources. Format: {name, downloads:[{title,uris,uploadDate,fileSize}]}.',cat_urls:'Source URLs',cat_refresh:'Fetch now',cat_none:'no source configured — the filehoster path is inactive',cat_items:'entries in total',cfg_warn:'Configuration',cfg_warn_hint:'One path is unusable — downloads taking it never even start.',notif_maillog:'Mail log',conn_scraper:'Scrapers / cover sources',sub_an:'active',sub_da:'configured but off',sub_leer:'not configured',details:'Details',nav_lists:'My lists',favourites:'Favourites',favourite:'Favourite',fav_empty:'No favourites yet.',fav_remove:'Remove',fav_hint:'Titles you want to get back to quickly. Unlike the wishlist, they never disappear on their own.',wl_hint_head:'Wishlist — what you do not have yet',flt_active:'active',flt_done:'done',flt_failed:'failed',flt_leer:'Nothing in this filter.',flt_denied:'denied',cov_measurable:'{n} of {m} consoles measurable',cov_method:'sum owned ÷ sum known — not the average of the percentages, which would weigh a small system like a large one.',bl_hint:'<b>Substring, not a regular expression.</b> An entry matches if it appears anywhere in the <b>title</b> — case is ignored, and characters like <code>.</code> or <code>*</code> stand for themselves. Only the <b>title</b> is checked, not the file name, release group or platform. The rule applies to search, discover and recommendations, and it <b>refuses new requests</b>. It does <b>not stop a request already running</b>, and it removes nothing already in the library. It applies to <b>every user</b> of this instance.',rate_title:'Rating',rate_mine:'your rating',rate_others:'others',rate_clear:'clear',comments:'Comments',comments_none:'No comments yet.',jd_hint:'Three views of the same handover: Romseerr sees the first two, JDownloader the third. Empty = default.',jd_watch:'Watch folder (Romseerr writes)',jd_out:'Finished folder (Romseerr reads)',jd_base:'Download base (JDownloader view)',var_prefs:'Release variants (region/language)',var_region_order:'Region order — the order is the preference',var_lang:'Preferred language',var_prerelease:'Accept beta/prototype/demo',var_unspec:'unspecified',var_preferred:'preferred',var_hint:'Instance-wide fallback for users who set nothing themselves. Region changes content (language, difficulty, censorship, 50/60 Hz) — that is not a quality ladder, so candidates follow this order rather than being sorted.',var_of:'Variant',ra_achievements:'achievements',ra_points:'points',ra_earned:'earned',ra_user:'RetroAchievements account (optional)',ra_refresh:'Fetch sets',ra_sets:'sets',ra_nokey:'no API key stored',ra_unmapped:'no console mapping',ra_only:'with achievements only',cov_of:'of',cov_src:'Source',cov_asof:'as of',cov_files:'files',cov_missing:'missing titles',cov_refresh:'Refresh catalogue',cov_nosnap:'no snapshot — catalogue not fetched yet',cov_nosource:'no catalogue source for this platform',cov_basis:'Based on a snapshot from {src} (max {max} titles per platform). Metadata sets disagree about what counts as a distinct title — the percentage is an orientation, not a measurement.',cov_search:'Search',cov_none:'Nothing missing (or no catalogue).',cov_filter:'Filter …',cov_filter_do:'Filter',cov_wish_sel:'Selection to wishlist',wl_import:'Import',wl_imp_hint:'Paste a list or pick a file (TXT/CSV) — one title per line, optionally title;platform. Nothing is written until you confirm the preview.',wl_imp_example:'Download example file',wl_imp_ph:'Chrono Trigger\nSuper Metroid;snes',wl_imp_preview:'Preview',wl_imp_apply:'Import',wl_imp_none:'Nothing selected.',wl_imp_done:'{a} imported, {s} skipped.',wl_imp_trunc:'Only the first {n} lines are checked.',wl_imp_toobig:'File too large (max 200 kB).',wl_imp_nocheck:'No IGDB credentials — no catalogue check; entries are imported unverified.',wl_s_matched:'matched',wl_s_ambiguous:'ambiguous',wl_s_notfound:'not found',wl_s_duplicate:'already listed',wl_s_inlib:'already in library',wl_s_unverified:'unverified',add_wishlist:'⭐ Watch',wl_added:'⭐ watched',wl_empty:'Wishlist empty.',wl_remove:'Remove',
 users:'Users',new_user:'Create new user',create:'Create',del:'Delete',autoapprove:'Auto-approve',role_user:'User',role_admin:'Admin',username:'Username',password:'Password',
 notif_discord:'Notifications — Discord',active:'enabled',test:'Test',save:'Save',saved:'saved ✓',test_sent:'test sent ✓',webhook_ph:'Discord webhook URL',
 st_pending:'⏳ Awaiting approval',st_queued:'Requested',st_downloading:'Downloading…',st_importing:'Processing',st_done:'✅ Available',st_error:'Error',st_denied:'Denied',st_exists:'in library',
 settings:'Settings',sec_general:'General',sec_notif:'Notifications',sec_users:'Users',sec_services:'Services',sec_about:'About',app_name:'App name',default_lang:'Default language',refresh:'Refresh',version:'Version',about_build:'Build',about_no_build:'Provenance unknown — this instance cannot say whether it matches the source.',upd_avail:'Update available:',upd_current:'up to date',about_txt:'Self-built Seerr clone for ROMs.',wiz_welcome:'Welcome to Romseerr',wiz_welcome_txt:'This wizard connects you to the stack services (SABnzbd, Prowlarr, IGDB, RomM) step by step. You can test or skip each step.',wiz_done:'All set!',wiz_done_txt:'Basic configuration is done. You can adjust everything later under Settings → Connections.',wiz_next:'Next',wiz_back:'Back',wiz_skip:'Skip',wiz_finish:'Get started',wiz_step:'Step',wiz_reopen:'Reopen wizard',about_lib:'Library',about_titles:'titles',about_platforms:'platforms',about_jobs:'Requests',about_active:'active',about_links:'Links',about_feat:'Features',about_feat_txt:'Search across Archive.org + Usenet, dedup, discover, requests with approval, users & permissions, quotas, notifications (Discord/Telegram/email/web push), issues, PWA, API.',about_stack:'Stack',about_stack_txt:'Orchestrates Prowlarr, SABnzbd, JDownloader and RomM. Connections configurable under Settings.',about_license:'License: MIT',sec_maint:'Logs & maintenance',exp_title:'Export / import',exp_hint:'Saves settings, users & permissions, requests and wishlists as JSON. Without a passphrase, secrets (passwords, API keys, webhook URLs) are LEFT OUT — with one they are attached encrypted. The same passphrase is needed on import.',exp_pass:'Passphrase',exp_pass_ph:'empty = without secrets',exp_do:'Export',exp_merge:'Merge',exp_replace:'Replace',imp_do:'Import',exp_done_plain:'Exported (without secrets).',exp_done_enc:'Exported (secrets encrypted).',imp_nofile:'No file selected.',imp_badjson:'File is not valid JSON.',imp_conf_merge:'Merge this import? Existing values are overwritten, anything not mentioned stays.',imp_conf_replace:'REPLACE? Users, requests and wishlists are fully replaced by the file.',imp_done:'Imported:',logs:'Log',clear_cache:'Clear cache',reindex:'Reindex',clear_finished:'Clear finished',done_word:'Done',lbl_jobs:'Requests',lbl_lib:'Library',sec_conn:'Connections',reveal:'Show in clear text',tls_hint:'Provide cert + key (PEM) — the app then also starts an HTTPS listener on the chosen port (restart required). For web push/PWA without a separate reverse proxy.',tls_none:'no certificate stored',tls_expires:'valid until',tls_key_note:'private key — never shown',tls_restart:'restart the container to activate',conn_hint:'Empty fields fall back to the environment (.env). Secrets are masked — leave blank to keep the current value.',un_check:'Check usenet path',un_hint:'Measures the chain search → category → queue → collect folder without downloading anything. The last line shows both views of the same folder — if they diverge, downloads finish but are never picked up.',un_search:'Search via Prowlarr',un_cat:'SAB category',un_queue:'Queue',un_collect:'Collect folder',
 profile:'Profile',display_name:'Display name',email:'Email',language:'Language',design:'Design',default_design:'Default design',d_seerr:'Seerr',d_glass:'Glass',d_clean:'Clean',avatar:'Avatar',pwebhook:'Personal Discord webhook',change_pw:'Change password',cur_pw:'Current password',new_pw:'New password',choose_img:'Choose image',saved_ok:'saved ✓',
 blocklist:'Blocklist',add_btn:'Add',pattern_ph:'Keyword/pattern in title',
 nav_issues:'🐞 Issues',nav_messages:'Messages',msg_to:'To',msg_none:'No messages yet.',msg_ph:'Write a message …',msg_send:'Send',msg_hint:'Ctrl+Enter sends',msg_nousers:'No other users.',req_for:'Request for',req_self:'myself',issues:'Issues',report_issue:'Report issue',issue_msg:'Message',close_btn:'Close',st_open:'open',st_closed:'closed',submit:'Submit',issue_type:'Type',comment_ph:'Write a comment …',comment_send:'Send',push_enable:'🔔 Enable push',push_disable:'🔕 Disable push',push_unsupported:'Push unavailable (needs HTTPS)',push_denied:'Permission denied',push_on:'Push enabled ✓',push_off:'Push disabled'
},fr:{
 nav_discover:'🔍 Découvrir',nav_requests:'📥 Demandes',nav_users:'👤 Utilisateurs',nav_settings:'⚙️ Paramètres',logout:'🚪 Déconnexion',
 search_ph:'Rechercher un jeu … (Entrée)',platforms:'Plateformes',all:'Toutes',selected:'sélectionné',
 hint_type:'Saisissez un titre et appuyez sur Entrée.',loading_home:'Chargement …',popular_on:'Populaire sur',click_search:'cliquer pour rechercher',
 searching:'Recherche …',no_results:'Aucun résultat.',results:'résultats',in_library:'✓ dans la bibliothèque',download:'⬇ Télécharger',requested:'✓ demandé',collection:'Collection',
 versions:'Versions / sources',files:'Fichiers',no_desc:'Aucune description disponible.',screenshots:'Captures',similar:'Jeux similaires',series:'Série',because_you:'Parce que vous avez demandé :',
 no_requests:'Aucune demande.',approve:'Approuver',deny:'Refuser',retry:'Réessayer',reset:'Tout réinitialiser',req_all:'Tout demander',flt_user:'Utilisateur',flt_all:'Tous',wishlist:'Liste de souhaits',nav_coverage:'Couverture',emu_install:'installer',emu_needs_url:'Pas de source automatique — indiquez l’URL dans le .env de l’hôte.',emu_needs_url_kurz:'URL requise',emu_rb_confirm:'Revenir à la version précédente de {n} ?',emu_rb_failed:'retour échoué',emu_update:'Mettre à jour les émulateurs',emu_nohost:'aucun hôte de diffusion',emu_nolauncher:'aucun service de lancement',emu_unreachable:'service injoignable',emu_running:'mise à jour en cours …',emu_none:'aucun émulateur installé',emu_ok:'dernier essai réussi',emu_failed:'dernier essai échoué',fw_hint:'Le BIOS et le firmware résident sur l’hôte de diffusion, pas dans Romseerr. Ce qui manque ici donne un écran noir dans le flux.',fw_ready:'complet',fw_notinstalled:'le fichier est là mais n’est pas installé dans l’émulateur — à installer une fois',fw_missing:'manquant',fw_badsize:'taille inattendue — téléchargement interrompu ?',fw_upload:'envoyer un fichier',fw_vendor:'récupérer chez le constructeur',fw_docs:'documentation',fw_nolauncher:'aucun service de lancement — état du firmware inconnu',fw_fetching:'téléchargement constructeur en cours …',fw_sending:'envoi',fw_failed:'envoi échoué',stream:'Diffuser',stream_single:'place unique — une session à la fois',stream_busy:'Occupé : {u} joue à {g}',stream_stop:'Terminer la session',stream_not_in_lib:'Le titre doit être dans la bibliothèque.',stream_no:'Diffusion indisponible.',stream_running:'▶ en cours — fenêtre ouverte',stream_manual:'bureau ouvert — lancez le titre là-bas',stream_failed:'échec du lancement — bureau ouvert',stream_title:'Hôte de diffusion',stream_hint:'Pour les plateformes que le navigateur ne peut pas émuler (PS2, GameCube, Wii, Switch).',stream_url_l:'URL navigateur de l’hôte',stream_launch_l:'Service de lancement (optionnel)',sec_outbound:'Requêtes sortantes',outbound_hint:'Les URLs de webhook viennent des utilisateurs. Par défaut, les cibles privées, loopback et link-local sont refusées. Autorisez-les explicitement si votre destination est sur le même réseau.',outbound_allow:'Autoriser les cibles en réseau privé',play:'Jouer dans le navigateur',play_no_romm:'Impossible — RomM n’est pas connecté.',play_no_core:'Cette plateforme ne peut pas être émulée dans le navigateur.',play_not_in_lib:'Le titre doit être dans la bibliothèque.',play_too_large:'Trop volumineux pour le navigateur (limite {mb} Mo).',play_no_title:'Aucun titre.',play_bios:'nécessite un BIOS',play_romset:'arcade : romset correspondant requis',cat_title:'Catalogues d’hébergeurs (expérimental)',cat_hint:'Sources JSON de catalogue, une URL par ligne. Volontairement non fournies — l’opérateur choisit les sources.',cat_urls:'URLs sources',cat_refresh:'Récupérer',cat_none:'aucune source — le chemin hébergeur est inactif',cat_items:'entrées au total',cfg_warn:'Configuration',cfg_warn_hint:'Une voie est inutilisable — les téléchargements qui l’empruntent ne démarrent pas.',notif_maillog:'Journal des mails',conn_scraper:'Scrapers / sources de jaquettes',sub_an:'actif',sub_da:'configuré mais inactif',sub_leer:'non configuré',details:'Détails',nav_lists:'Mes listes',favourites:'Favoris',favourite:'Favori',fav_empty:'Aucun favori.',fav_remove:'Retirer',fav_hint:'Les titres que vous voulez retrouver vite. Contrairement à la liste de souhaits, ils ne disparaissent jamais tout seuls.',wl_hint_head:'Liste de souhaits — ce que vous n’avez pas encore',flt_active:'actifs',flt_done:'terminés',flt_failed:'échoués',flt_leer:'Rien dans ce filtre.',flt_denied:'refusés',cov_measurable:'{n} sur {m} consoles mesurables',cov_method:'somme possédée ÷ somme connue — pas la moyenne des pourcentages.',bl_hint:'<b>Sous-chaîne, pas une expression régulière.</b> Une entrée s’applique si elle apparaît dans le <b>titre</b> — la casse est ignorée. Seul le <b>titre</b> est vérifié. La règle agit sur la recherche, la découverte et les recommandations et <b>refuse les nouvelles demandes</b>. Elle <b>n’arrête pas une demande en cours</b> et ne supprime rien. Elle vaut pour <b>tous les utilisateurs</b>.',rate_title:'Note',rate_mine:'votre note',rate_others:'autres',rate_clear:'retirer',comments:'Commentaires',comments_none:'Aucun commentaire.',jd_hint:'Trois vues du même transfert : Romseerr voit les deux premières, JDownloader la troisième. Vide = défaut.',jd_watch:'Dossier surveillé (Romseerr écrit)',jd_out:'Dossier terminé (Romseerr lit)',jd_base:'Base de téléchargement (vue JDownloader)',var_prefs:'Versions (région/langue)',var_region_order:'Ordre des régions — l’ordre est la préférence',var_lang:'Langue préférée',var_prerelease:'Accepter bêta/prototype/démo',var_unspec:'non spécifié',var_preferred:'préféré',var_hint:'Repli pour toute l’instance. La région change le contenu (langue, difficulté, censure, 50/60 Hz) — ce n’est pas une échelle de qualité.',var_of:'Version',ra_achievements:'succès',ra_points:'points',ra_earned:'obtenus',ra_user:'Compte RetroAchievements (optionnel)',ra_refresh:'Récupérer les sets',ra_sets:'sets',ra_nokey:'aucune clé API',ra_unmapped:'sans correspondance de console',ra_only:'avec succès seulement',cov_of:'sur',cov_src:'Source',cov_asof:'au',cov_files:'fichiers',cov_missing:'titres manquants',cov_refresh:'Actualiser le catalogue',cov_nosnap:'pas d’instantané — catalogue pas encore récupéré',cov_nosource:'pas de source de catalogue pour cette plateforme',cov_basis:'Basé sur un instantané de {src} (max {max} titres par plateforme). Les jeux de métadonnées ne s’accordent pas sur ce qui compte comme titre distinct — le pourcentage est une orientation, pas une mesure.',cov_search:'Chercher',cov_none:'Rien ne manque (ou pas de catalogue).',cov_filter:'Filtrer …',cov_filter_do:'Filtrer',cov_wish_sel:'Sélection vers la liste',wl_import:'Import',wl_imp_hint:'Collez une liste ou choisissez un fichier (TXT/CSV) — un titre par ligne, éventuellement titre;plateforme. Rien n’est écrit avant votre confirmation.',wl_imp_example:'Télécharger un exemple',wl_imp_ph:'Chrono Trigger\nSuper Metroid;snes',wl_imp_preview:'Aperçu',wl_imp_apply:'Importer',wl_imp_none:'Rien de sélectionné.',wl_imp_done:'{a} importés, {s} ignorés.',wl_imp_trunc:'Seules les {n} premières lignes sont vérifiées.',wl_imp_toobig:'Fichier trop grand (max 200 ko).',wl_imp_nocheck:'Sans accès IGDB, pas de vérification — les entrées sont importées telles quelles.',wl_s_matched:'trouvé',wl_s_ambiguous:'ambigu',wl_s_notfound:'introuvable',wl_s_duplicate:'déjà suivi',wl_s_inlib:'déjà présent',wl_s_unverified:'non vérifié',add_wishlist:'⭐ Suivre',wl_added:'⭐ suivi',wl_empty:'Liste vide.',wl_remove:'Retirer',
 users:'Utilisateurs',new_user:'Créer un utilisateur',create:'Créer',del:'Supprimer',autoapprove:'Approbation auto',role_user:'Utilisateur',role_admin:'Admin',username:"Nom d'utilisateur",password:'Mot de passe',
 notif_discord:'Notifications — Discord',active:'activé',test:'Test',save:'Enregistrer',saved:'enregistré ✓',test_sent:'test envoyé ✓',webhook_ph:'URL du webhook Discord',
 st_pending:"⏳ En attente d'approbation",st_queued:'Demandé',st_downloading:'Téléchargement…',st_importing:'Traitement',st_done:'✅ Disponible',st_error:'Erreur',st_denied:'Refusé',st_exists:'présent',
 settings:'Paramètres',sec_general:'Général',sec_notif:'Notifications',sec_users:'Utilisateurs',sec_services:'Services',sec_about:'À propos',app_name:"Nom de l'app",default_lang:'Langue par défaut',refresh:'Actualiser',version:'Version',about_build:'Build',about_no_build:'Origine inconnue — cette instance ne peut pas dire si elle correspond aux sources.',upd_avail:'Mise à jour disponible :',upd_current:'à jour',about_txt:'Clone de Seerr pour ROMs, fait maison.',wiz_welcome:'Bienvenue sur Romseerr',wiz_welcome_txt:'Cet assistant vous connecte aux services du stack (SABnzbd, Prowlarr, IGDB, RomM) étape par étape. Vous pouvez tester ou passer chaque étape.',wiz_done:'Terminé !',wiz_done_txt:'La configuration de base est prête. Vous pouvez tout ajuster plus tard dans Paramètres → Connexions.',wiz_next:'Suivant',wiz_back:'Retour',wiz_skip:'Passer',wiz_finish:'Commencer',wiz_step:'Étape',wiz_reopen:'Rouvrir l’assistant',about_lib:'Bibliothèque',about_titles:'titres',about_platforms:'plateformes',about_jobs:'Demandes',about_active:'actives',about_links:'Liens',about_feat:'Fonctions',about_feat_txt:'Recherche Archive.org + Usenet, dédup, découverte, demandes avec approbation, utilisateurs & droits, quotas, notifications, problèmes, PWA, API.',about_stack:'Stack',about_stack_txt:'Orchestre Prowlarr, SABnzbd, JDownloader et RomM. Connexions configurables dans Paramètres.',about_license:'Licence : MIT',sec_maint:'Journaux & maintenance',exp_title:'Export / import',exp_hint:'Sauvegarde paramètres, utilisateurs & droits, demandes et listes de souhaits en JSON. Sans phrase secrète, les secrets (mots de passe, clés API, URLs de webhook) sont EXCLUS — avec, ils sont joints chiffrés. La même phrase est requise à l’import.',exp_pass:'Phrase secrète',exp_pass_ph:'vide = sans secrets',exp_do:'Exporter',exp_merge:'Fusionner',exp_replace:'Remplacer',imp_do:'Importer',exp_done_plain:'Exporté (sans secrets).',exp_done_enc:'Exporté (secrets chiffrés).',imp_nofile:'Aucun fichier choisi.',imp_badjson:'Le fichier n’est pas du JSON valide.',imp_conf_merge:'Fusionner cet import ? Les valeurs existantes sont écrasées.',imp_conf_replace:'REMPLACER ? Utilisateurs, demandes et listes seront entièrement remplacés.',imp_done:'Importé :',logs:'Journal',clear_cache:'Vider le cache',reindex:'Réindexer',clear_finished:'Effacer terminés',done_word:'Terminé',lbl_jobs:'Demandes',lbl_lib:'Bibliothèque',sec_conn:'Connexions',reveal:'Afficher en clair',tls_hint:'Fournir le certificat + la clé (PEM) — l’app démarre alors un écouteur HTTPS sur le port choisi (redémarrage requis).',tls_none:'aucun certificat',tls_expires:'valide jusqu’au',tls_key_note:'clé privée — jamais affichée',tls_restart:'redémarrer le conteneur pour activer',conn_hint:'Les champs vides utilisent la valeur de l’environnement (.env). Les secrets sont masqués — laisser vide conserve la valeur.',un_check:'Vérifier le chemin Usenet',un_hint:'Mesure la chaîne recherche → catégorie → file → dossier de récupération sans rien télécharger. La dernière ligne montre les deux vues du même dossier — si elles divergent, les téléchargements aboutissent mais ne sont jamais repris.',un_search:'Recherche via Prowlarr',un_cat:'Catégorie SAB',un_queue:'File d’attente',un_collect:'Dossier de récupération',
 profile:'Profil',display_name:'Nom affiché',email:'E-mail',language:'Langue',design:'Thème',default_design:'Thème par défaut',d_seerr:'Seerr',d_glass:'Verre',d_clean:'Épuré',avatar:'Avatar',pwebhook:'Webhook Discord personnel',change_pw:'Changer le mot de passe',cur_pw:'Mot de passe actuel',new_pw:'Nouveau mot de passe',choose_img:'Choisir une image',saved_ok:'enregistré ✓',
 blocklist:'Liste de blocage',add_btn:'Ajouter',pattern_ph:'Mot-clé/motif dans le titre',
 nav_issues:'🐞 Problèmes',nav_messages:'Messages',msg_to:'À',msg_none:'Aucun message.',msg_ph:'Écrire un message …',msg_send:'Envoyer',msg_hint:'Ctrl+Entrée envoie',msg_nousers:'Aucun autre utilisateur.',req_for:'Demande pour',req_self:'moi-même',issues:'Problèmes',report_issue:'Signaler un problème',issue_msg:'Message',close_btn:'Fermer',st_open:'ouvert',st_closed:'fermé',submit:'Envoyer',issue_type:'Type',comment_ph:'Écrire un commentaire …',comment_send:'Envoyer',push_enable:'🔔 Activer push',push_disable:'🔕 Désactiver push',push_unsupported:'Push indisponible (HTTPS requis)',push_denied:'Permission refusée',push_on:'Push activé ✓',push_off:'Push désactivé'
},es:{
 nav_discover:'🔍 Descubrir',nav_requests:'📥 Solicitudes',nav_users:'👤 Usuarios',nav_settings:'⚙️ Ajustes',logout:'🚪 Salir',
 search_ph:'Buscar un juego … (Intro)',platforms:'Plataformas',all:'Todas',selected:'seleccionado',
 hint_type:'Escribe un título y pulsa Intro.',loading_home:'Cargando …',popular_on:'Popular en',click_search:'clic para buscar',
 searching:'Buscando …',no_results:'Sin resultados.',results:'resultados',in_library:'✓ en la biblioteca',download:'⬇ Descargar',requested:'✓ solicitado',collection:'Colección',
 versions:'Versiones / fuentes',files:'Archivos',no_desc:'Sin descripción disponible.',screenshots:'Capturas',similar:'Juegos similares',series:'Serie',because_you:'Porque solicitaste:',
 no_requests:'Aún no hay solicitudes.',approve:'Aprobar',deny:'Rechazar',retry:'Reintentar',reset:'Restablecer todo',req_all:'Solicitar todo',flt_user:'Usuario',flt_all:'Todos',wishlist:'Lista de deseos',nav_coverage:'Cobertura',emu_install:'instalar',emu_needs_url:'Sin fuente automática — indica la URL en el .env del host.',emu_needs_url_kurz:'URL necesaria',emu_rb_confirm:'¿Volver {n} a la versión anterior?',emu_rb_failed:'reversión fallida',emu_update:'Actualizar emuladores',emu_nohost:'sin host de transmisión',emu_nolauncher:'sin servicio de lanzamiento',emu_unreachable:'servicio inalcanzable',emu_running:'actualización en curso …',emu_none:'sin emuladores instalados',emu_ok:'última vez correcto',emu_failed:'última vez fallido',fw_hint:'La BIOS y el firmware están en el host de streaming, no en Romseerr. Lo que falte aquí acaba como pantalla negra en el stream.',fw_ready:'completo',fw_notinstalled:'el archivo está pero no instalado en el emulador — instálalo allí una vez',fw_missing:'falta',fw_badsize:'tamaño inesperado — ¿descarga interrumpida?',fw_upload:'subir archivo',fw_vendor:'obtener del fabricante',fw_docs:'documentación',fw_nolauncher:'sin servicio de arranque — estado del firmware desconocido',fw_fetching:'descarga del fabricante en curso …',fw_sending:'subiendo',fw_failed:'subida fallida',stream:'Transmitir',stream_single:'plaza única — una sesión a la vez',stream_busy:'Ocupado: {u} está jugando {g}',stream_stop:'Terminar sesión',stream_not_in_lib:'El título debe estar en la biblioteca.',stream_no:'Transmisión no disponible.',stream_running:'▶ en marcha — ventana abierta',stream_manual:'escritorio abierto — inicia el título allí',stream_failed:'fallo al iniciar — escritorio abierto',stream_title:'Host de transmisión',stream_hint:'Para plataformas que el navegador no puede emular (PS2, GameCube, Wii, Switch).',stream_url_l:'URL del host en el navegador',stream_launch_l:'Servicio de lanzamiento (opcional)',sec_outbound:'Peticiones salientes',outbound_hint:'Las URLs de webhook las ponen los usuarios. Por defecto se rechazan destinos privados, loopback y link-local. Permítelos explícitamente si tu destino está en la misma red.',outbound_allow:'Permitir destinos en red privada',play:'Jugar en el navegador',play_no_romm:'No es posible — RomM no está conectado.',play_no_core:'Esta plataforma no se puede emular en el navegador.',play_not_in_lib:'El título debe estar en la biblioteca.',play_too_large:'Demasiado grande para el navegador (límite {mb} MB).',play_no_title:'Sin título.',play_bios:'necesita BIOS',play_romset:'arcade: solo con el romset adecuado',cat_title:'Catálogos de hosters (experimental)',cat_hint:'Fuentes JSON de catálogo, una URL por línea. Deliberadamente no incluidas — el operador elige las fuentes.',cat_urls:'URLs de origen',cat_refresh:'Obtener ahora',cat_none:'sin fuente — la vía de hoster está inactiva',cat_items:'entradas en total',cfg_warn:'Configuración',cfg_warn_hint:'Una vía no se puede usar — las descargas por ahí ni siquiera empiezan.',notif_maillog:'Registro de correo',conn_scraper:'Scrapers / fuentes de carátulas',sub_an:'activo',sub_da:'configurado pero apagado',sub_leer:'sin configurar',details:'Detalles',nav_lists:'Mis listas',favourites:'Favoritos',favourite:'Favorito',fav_empty:'Aún no hay favoritos.',fav_remove:'Quitar',fav_hint:'Títulos que quieres reencontrar rápido. A diferencia de la lista de deseos, nunca desaparecen solos.',wl_hint_head:'Lista de deseos — lo que aún no tienes',flt_active:'activos',flt_done:'terminados',flt_failed:'fallidos',flt_leer:'Nada en este filtro.',flt_denied:'rechazados',cov_measurable:'{n} de {m} consolas medibles',cov_method:'suma en posesión ÷ suma conocida — no el promedio de los porcentajes.',bl_hint:'<b>Subcadena, no una expresión regular.</b> Una entrada coincide si aparece en el <b>título</b> — sin distinguir mayúsculas. Solo se comprueba el <b>título</b>. La regla afecta a la búsqueda, a descubrir y a las recomendaciones y <b>rechaza solicitudes nuevas</b>. <b>No detiene una solicitud en curso</b> ni borra nada. Se aplica a <b>todos los usuarios</b>.',rate_title:'Valoración',rate_mine:'tu valoración',rate_others:'otros',rate_clear:'quitar',comments:'Comentarios',comments_none:'Sin comentarios.',jd_hint:'Tres vistas de la misma entrega: Romseerr ve las dos primeras, JDownloader la tercera. Vacío = predeterminado.',jd_watch:'Carpeta vigilada (escribe Romseerr)',jd_out:'Carpeta terminada (lee Romseerr)',jd_base:'Base de descarga (vista de JDownloader)',var_prefs:'Versiones (región/idioma)',var_region_order:'Orden de regiones — el orden es la preferencia',var_lang:'Idioma preferido',var_prerelease:'Aceptar beta/prototipo/demo',var_unspec:'sin especificar',var_preferred:'preferida',var_hint:'Valor de reserva para toda la instancia. La región cambia el contenido (idioma, dificultad, censura, 50/60 Hz) — no es una escala de calidad.',var_of:'Versión',ra_achievements:'logros',ra_points:'puntos',ra_earned:'obtenidos',ra_user:'Cuenta RetroAchievements (opcional)',ra_refresh:'Obtener sets',ra_sets:'sets',ra_nokey:'sin clave API',ra_unmapped:'sin correspondencia de consola',ra_only:'solo con logros',cov_of:'de',cov_src:'Fuente',cov_asof:'a fecha',cov_files:'archivos',cov_missing:'títulos que faltan',cov_refresh:'Actualizar catálogo',cov_nosnap:'sin instantánea — catálogo aún no obtenido',cov_nosource:'sin fuente de catálogo para esta plataforma',cov_basis:'Basado en una instantánea de {src} (máx. {max} títulos por plataforma). Los conjuntos de metadatos no coinciden en qué cuenta como título propio — el porcentaje orienta, no mide.',cov_search:'Buscar',cov_none:'No falta nada (o no hay catálogo).',cov_filter:'Filtrar …',cov_filter_do:'Filtrar',cov_wish_sel:'Selección a la lista',wl_import:'Importar',wl_imp_hint:'Pega una lista o elige un archivo (TXT/CSV) — un título por línea, opcionalmente título;plataforma. No se escribe nada hasta que confirmes.',wl_imp_example:'Descargar archivo de ejemplo',wl_imp_ph:'Chrono Trigger\nSuper Metroid;snes',wl_imp_preview:'Vista previa',wl_imp_apply:'Importar',wl_imp_none:'Nada seleccionado.',wl_imp_done:'{a} importados, {s} omitidos.',wl_imp_trunc:'Solo se comprueban las primeras {n} líneas.',wl_imp_toobig:'Archivo demasiado grande (máx. 200 kB).',wl_imp_nocheck:'Sin acceso a IGDB no hay comprobación — se importan sin verificar.',wl_s_matched:'encontrado',wl_s_ambiguous:'ambiguo',wl_s_notfound:'no encontrado',wl_s_duplicate:'ya en la lista',wl_s_inlib:'ya en biblioteca',wl_s_unverified:'sin verificar',add_wishlist:'⭐ Seguir',wl_added:'⭐ en lista',wl_empty:'Lista vacía.',wl_remove:'Quitar',
 users:'Usuarios',new_user:'Crear usuario',create:'Crear',del:'Eliminar',autoapprove:'Auto-aprobación',role_user:'Usuario',role_admin:'Admin',username:'Usuario',password:'Contraseña',
 notif_discord:'Notificaciones — Discord',active:'activo',test:'Prueba',save:'Guardar',saved:'guardado ✓',test_sent:'prueba enviada ✓',webhook_ph:'URL del webhook de Discord',
 st_pending:'⏳ Esperando aprobación',st_queued:'Solicitado',st_downloading:'Descargando…',st_importing:'Procesando',st_done:'✅ Disponible',st_error:'Error',st_denied:'Rechazado',st_exists:'presente',
 settings:'Ajustes',sec_general:'General',sec_notif:'Notificaciones',sec_users:'Usuarios',sec_services:'Servicios',sec_about:'Acerca de',app_name:'Nombre de la app',default_lang:'Idioma predeterminado',refresh:'Actualizar',version:'Versión',about_build:'Build',about_no_build:'Origen desconocido — esta instancia no puede decir si coincide con las fuentes.',upd_avail:'Actualización disponible:',upd_current:'actualizado',about_txt:'Clon de Seerr para ROMs, hecho en casa.',wiz_welcome:'Bienvenido a Romseerr',wiz_welcome_txt:'Este asistente te conecta con los servicios del stack (SABnzbd, Prowlarr, IGDB, RomM) paso a paso. Puedes probar u omitir cada paso.',wiz_done:'¡Listo!',wiz_done_txt:'La configuración básica está hecha. Puedes ajustar todo luego en Ajustes → Conexiones.',wiz_next:'Siguiente',wiz_back:'Atrás',wiz_skip:'Omitir',wiz_finish:'Empezar',wiz_step:'Paso',wiz_reopen:'Reabrir asistente',about_lib:'Biblioteca',about_titles:'títulos',about_platforms:'plataformas',about_jobs:'Solicitudes',about_active:'activas',about_links:'Enlaces',about_feat:'Funciones',about_feat_txt:'Búsqueda en Archive.org + Usenet, dedup, descubrir, solicitudes con aprobación, usuarios y permisos, cuotas, notificaciones, problemas, PWA, API.',about_stack:'Stack',about_stack_txt:'Orquesta Prowlarr, SABnzbd, JDownloader y RomM. Conexiones configurables en Ajustes.',about_license:'Licencia: MIT',sec_maint:'Registros y mantenimiento',exp_title:'Exportar / importar',exp_hint:'Guarda ajustes, usuarios y permisos, solicitudes y listas de deseos como JSON. Sin frase de contraseña los secretos (contraseñas, claves API, URLs de webhook) QUEDAN FUERA — con ella se adjuntan cifrados. La misma frase hace falta al importar.',exp_pass:'Frase de contraseña',exp_pass_ph:'vacío = sin secretos',exp_do:'Exportar',exp_merge:'Combinar',exp_replace:'Reemplazar',imp_do:'Importar',exp_done_plain:'Exportado (sin secretos).',exp_done_enc:'Exportado (secretos cifrados).',imp_nofile:'Ningún archivo seleccionado.',imp_badjson:'El archivo no es JSON válido.',imp_conf_merge:'¿Combinar esta importación? Los valores existentes se sobrescriben.',imp_conf_replace:'¿REEMPLAZAR? Usuarios, solicitudes y listas se sustituyen por completo.',imp_done:'Importado:',logs:'Registro',clear_cache:'Vaciar caché',reindex:'Reindexar',clear_finished:'Borrar terminados',done_word:'Hecho',lbl_jobs:'Solicitudes',lbl_lib:'Biblioteca',sec_conn:'Conexiones',reveal:'Mostrar en texto plano',tls_hint:'Proporciona certificado + clave (PEM) — la app inicia además un listener HTTPS en el puerto elegido (requiere reinicio).',tls_none:'sin certificado',tls_expires:'válido hasta',tls_key_note:'clave privada — nunca se muestra',tls_restart:'reinicia el contenedor para activar',conn_hint:'Los campos vacíos usan el valor del entorno (.env). Los secretos se enmascaran — dejar vacío conserva el valor.',un_check:'Comprobar la ruta Usenet',un_hint:'Mide la cadena búsqueda → categoría → cola → carpeta de recogida sin descargar nada. La última línea muestra ambas vistas de la misma carpeta — si divergen, las descargas terminan pero nunca se recogen.',un_search:'Búsqueda vía Prowlarr',un_cat:'Categoría SAB',un_queue:'Cola',un_collect:'Carpeta de recogida',
 profile:'Perfil',display_name:'Nombre visible',email:'Correo',language:'Idioma',design:'Diseño',default_design:'Diseño predeterminado',d_seerr:'Seerr',d_glass:'Cristal',d_clean:'Limpio',avatar:'Avatar',pwebhook:'Webhook de Discord personal',change_pw:'Cambiar contraseña',cur_pw:'Contraseña actual',new_pw:'Nueva contraseña',choose_img:'Elegir imagen',saved_ok:'guardado ✓',
 blocklist:'Lista de bloqueo',add_btn:'Añadir',pattern_ph:'Palabra clave/patrón en el título',
 nav_issues:'🐞 Problemas',nav_messages:'Mensajes',msg_to:'Para',msg_none:'Sin mensajes.',msg_ph:'Escribe un mensaje …',msg_send:'Enviar',msg_hint:'Ctrl+Enter envía',msg_nousers:'No hay otros usuarios.',req_for:'Solicitud para',req_self:'yo mismo',issues:'Problemas',report_issue:'Informar problema',issue_msg:'Mensaje',close_btn:'Cerrar',st_open:'abierto',st_closed:'cerrado',submit:'Enviar',issue_type:'Tipo',comment_ph:'Escribe un comentario …',comment_send:'Enviar',push_enable:'🔔 Activar push',push_disable:'🔕 Desactivar push',push_unsupported:'Push no disponible (requiere HTTPS)',push_denied:'Permiso denegado',push_on:'Push activado ✓',push_off:'Push desactivado'
},it:{
 nav_discover:'🔍 Scopri',nav_requests:'📥 Richieste',nav_users:'👤 Utenti',nav_settings:'⚙️ Impostazioni',logout:'🚪 Esci',
 search_ph:'Cerca un gioco … (Invio)',platforms:'Piattaforme',all:'Tutte',selected:'selezionate',
 hint_type:'Digita un titolo e premi Invio.',loading_home:'Caricamento …',popular_on:'Popolari su',click_search:'clicca per cercare',
 searching:'Ricerca …',no_results:'Nessun risultato.',results:'risultati',in_library:'✓ in libreria',download:'⬇ Scarica',requested:'✓ richiesto',collection:'Collezione',
 versions:'Versioni / fonti',files:'File',no_desc:'Nessuna descrizione disponibile.',screenshots:'Screenshot',similar:'Giochi simili',series:'Serie',because_you:'Perché hai richiesto:',
 no_requests:'Ancora nessuna richiesta.',approve:'Approva',deny:'Rifiuta',retry:'Riprova',reset:'Reimposta tutto',req_all:'Richiedi tutto',flt_user:'Utente',flt_all:'Tutti',wishlist:'Lista dei desideri',nav_coverage:'Copertura',emu_install:'installa',emu_needs_url:'Nessuna fonte automatica — indica l’URL nel .env dell’host.',emu_needs_url_kurz:'URL richiesta',emu_rb_confirm:'Ripristinare {n} alla versione precedente?',emu_rb_failed:'ripristino fallito',emu_update:'Aggiorna emulatori',emu_nohost:'nessun host di streaming',emu_nolauncher:'nessun servizio di avvio',emu_unreachable:'servizio irraggiungibile',emu_running:'aggiornamento in corso …',emu_none:'nessun emulatore installato',emu_ok:'ultima esecuzione riuscita',emu_failed:'ultima esecuzione fallita',fw_hint:'BIOS e firmware risiedono sull’host di streaming, non in Romseerr. Ciò che manca qui diventa schermo nero nello stream.',fw_ready:'completo',fw_notinstalled:'il file c’è ma non è installato nell’emulatore — installalo lì una volta',fw_missing:'mancante',fw_badsize:'dimensione inattesa — download interrotto?',fw_upload:'carica file',fw_vendor:'scarica dal produttore',fw_docs:'documentazione',fw_nolauncher:'nessun servizio di avvio — stato del firmware sconosciuto',fw_fetching:'download dal produttore in corso …',fw_sending:'invio',fw_failed:'invio fallito',stream:'Trasmetti',stream_single:'posto singolo — una sessione alla volta',stream_busy:'Occupato: {u} sta giocando a {g}',stream_stop:'Termina sessione',stream_not_in_lib:'Il titolo deve essere in libreria.',stream_no:'Streaming non disponibile.',stream_running:'▶ in esecuzione — finestra aperta',stream_manual:'desktop aperto — avvia lì il titolo',stream_failed:'avvio fallito — desktop aperto',stream_title:'Host di streaming',stream_hint:'Per piattaforme che il browser non può emulare (PS2, GameCube, Wii, Switch).',stream_url_l:'URL del host nel browser',stream_launch_l:'Servizio di avvio (opzionale)',sec_outbound:'Richieste in uscita',outbound_hint:'Gli URL dei webhook li imposta l’utente. Per impostazione predefinita i destinatari privati, loopback e link-local vengono rifiutati. Consentili esplicitamente se il tuo destinatario è nella stessa rete.',outbound_allow:'Consenti destinatari in rete privata',play:'Gioca nel browser',play_no_romm:'Non possibile — RomM non è connesso.',play_no_core:'Questa piattaforma non è emulabile nel browser.',play_not_in_lib:'Il titolo deve essere in libreria.',play_too_large:'Troppo grande per il browser (limite {mb} MB).',play_no_title:'Nessun titolo.',play_bios:'richiede il BIOS',play_romset:'arcade: solo con il romset corretto',cat_title:'Cataloghi filehoster (sperimentale)',cat_hint:'Fonti JSON di catalogo, una URL per riga. Volutamente non incluse — le fonti le sceglie l’operatore.',cat_urls:'URL delle fonti',cat_refresh:'Recupera ora',cat_none:'nessuna fonte — il percorso filehoster è inattivo',cat_items:'voci in totale',cfg_warn:'Configurazione',cfg_warn_hint:'Un percorso non è utilizzabile — i download che lo usano non partono nemmeno.',notif_maillog:'Registro email',conn_scraper:'Scraper / fonti copertine',sub_an:'attivo',sub_da:'configurato ma spento',sub_leer:'non configurato',details:'Dettagli',nav_lists:'Le mie liste',favourites:'Preferiti',favourite:'Preferito',fav_empty:'Nessun preferito.',fav_remove:'Rimuovi',fav_hint:'Titoli che vuoi ritrovare in fretta. A differenza della lista dei desideri, non spariscono mai da soli.',wl_hint_head:'Lista dei desideri — ciò che non hai ancora',flt_active:'attivi',flt_done:'completati',flt_failed:'falliti',flt_leer:'Niente in questo filtro.',flt_denied:'rifiutati',cov_measurable:'{n} di {m} console misurabili',cov_method:'somma posseduta ÷ somma nota — non la media delle percentuali.',bl_hint:'<b>Sottostringa, non un’espressione regolare.</b> Una voce corrisponde se compare nel <b>titolo</b> — maiuscole/minuscole indifferenti. Viene controllato solo il <b>titolo</b>. La regola vale per ricerca, scoperta e consigli e <b>rifiuta nuove richieste</b>. <b>Non ferma una richiesta già in corso</b> e non elimina nulla. Vale per <b>tutti gli utenti</b>.',rate_title:'Valutazione',rate_mine:'la tua valutazione',rate_others:'altri',rate_clear:'rimuovi',comments:'Commenti',comments_none:'Nessun commento.',jd_hint:'Tre viste sullo stesso passaggio: Romseerr vede le prime due, JDownloader la terza. Vuoto = predefinito.',jd_watch:'Cartella osservata (scrive Romseerr)',jd_out:'Cartella completata (legge Romseerr)',jd_base:'Base di download (vista JDownloader)',var_prefs:'Versioni (regione/lingua)',var_region_order:'Ordine delle regioni — l’ordine è la preferenza',var_lang:'Lingua preferita',var_prerelease:'Accetta beta/prototipo/demo',var_unspec:'non specificato',var_preferred:'preferita',var_hint:'Ripiego per tutta l’istanza. La regione cambia il contenuto (lingua, difficoltà, censura, 50/60 Hz) — non è una scala di qualità.',var_of:'Versione',ra_achievements:'obiettivi',ra_points:'punti',ra_earned:'ottenuti',ra_user:'Account RetroAchievements (opzionale)',ra_refresh:'Recupera i set',ra_sets:'set',ra_nokey:'nessuna chiave API',ra_unmapped:'senza mappatura console',ra_only:'solo con obiettivi',cov_of:'di',cov_src:'Fonte',cov_asof:'al',cov_files:'file',cov_missing:'titoli mancanti',cov_refresh:'Aggiorna catalogo',cov_nosnap:'nessuna istantanea — catalogo non ancora recuperato',cov_nosource:'nessuna fonte di catalogo per questa piattaforma',cov_basis:'Basato su un’istantanea da {src} (max {max} titoli per piattaforma). I set di metadati non concordano su cosa sia un titolo distinto — la percentuale orienta, non misura.',cov_search:'Cerca',cov_none:'Non manca nulla (o nessun catalogo).',cov_filter:'Filtra …',cov_filter_do:'Filtra',cov_wish_sel:'Selezione alla lista',wl_import:'Importa',wl_imp_hint:'Incolla un elenco o scegli un file (TXT/CSV) — un titolo per riga, opzionalmente titolo;piattaforma. Nulla viene scritto prima della conferma.',wl_imp_example:'Scarica file di esempio',wl_imp_ph:'Chrono Trigger\nSuper Metroid;snes',wl_imp_preview:'Anteprima',wl_imp_apply:'Importa',wl_imp_none:'Niente selezionato.',wl_imp_done:'{a} importati, {s} saltati.',wl_imp_trunc:'Vengono controllate solo le prime {n} righe.',wl_imp_toobig:'File troppo grande (max 200 kB).',wl_imp_nocheck:'Senza accesso IGDB nessun controllo — le voci vengono importate non verificate.',wl_s_matched:'trovato',wl_s_ambiguous:'ambiguo',wl_s_notfound:'non trovato',wl_s_duplicate:'già in lista',wl_s_inlib:'già in libreria',wl_s_unverified:'non verificato',add_wishlist:'⭐ Segui',wl_added:'⭐ seguito',wl_empty:'Lista vuota.',wl_remove:'Rimuovi',
 users:'Utenti',new_user:'Crea utente',create:'Crea',del:'Elimina',autoapprove:'Auto-approvazione',role_user:'Utente',role_admin:'Admin',username:'Utente',password:'Password',
 notif_discord:'Notifiche — Discord',active:'attivo',test:'Test',save:'Salva',saved:'salvato ✓',test_sent:'test inviato ✓',webhook_ph:'URL webhook Discord',
 st_pending:'⏳ In attesa di approvazione',st_queued:'Richiesto',st_downloading:'Scaricamento…',st_importing:'Elaborazione',st_done:'✅ Disponibile',st_error:'Errore',st_denied:'Rifiutato',st_exists:'presente',
 settings:'Impostazioni',sec_general:'Generale',sec_notif:'Notifiche',sec_users:'Utenti',sec_services:'Servizi',sec_about:'Informazioni',app_name:'Nome dell’app',default_lang:'Lingua predefinita',refresh:'Aggiorna',version:'Versione',about_build:'Build',about_no_build:'Origine sconosciuta — questa istanza non puo dire se corrisponde ai sorgenti.',upd_avail:'Aggiornamento disponibile:',upd_current:'aggiornato',about_txt:'Clone di Seerr per ROM, fatto in casa.',wiz_welcome:'Benvenuto in Romseerr',wiz_welcome_txt:'Questa procedura ti collega ai servizi dello stack (SABnzbd, Prowlarr, IGDB, RomM) passo dopo passo. Puoi testare o saltare ogni passaggio.',wiz_done:'Fatto!',wiz_done_txt:'La configurazione di base è pronta. Puoi regolare tutto in seguito in Impostazioni → Connessioni.',wiz_next:'Avanti',wiz_back:'Indietro',wiz_skip:'Salta',wiz_finish:'Inizia',wiz_step:'Passo',wiz_reopen:'Riapri procedura',about_lib:'Libreria',about_titles:'titoli',about_platforms:'piattaforme',about_jobs:'Richieste',about_active:'attive',about_links:'Link',about_feat:'Funzioni',about_feat_txt:'Ricerca su Archive.org + Usenet, dedup, scoperta, richieste con approvazione, utenti e permessi, quote, notifiche, problemi, PWA, API.',about_stack:'Stack',about_stack_txt:'Orchestra Prowlarr, SABnzbd, JDownloader e RomM. Connessioni configurabili nelle Impostazioni.',about_license:'Licenza: MIT',sec_maint:'Log e manutenzione',exp_title:'Esporta / importa',exp_hint:'Salva impostazioni, utenti e permessi, richieste e liste dei desideri come JSON. Senza passphrase i segreti (password, chiavi API, URL webhook) restano ESCLUSI — con la passphrase vengono allegati cifrati. La stessa passphrase serve all’importazione.',exp_pass:'Passphrase',exp_pass_ph:'vuoto = senza segreti',exp_do:'Esporta',exp_merge:'Unisci',exp_replace:'Sostituisci',imp_do:'Importa',exp_done_plain:'Esportato (senza segreti).',exp_done_enc:'Esportato (segreti cifrati).',imp_nofile:'Nessun file scelto.',imp_badjson:'Il file non è JSON valido.',imp_conf_merge:'Unire questa importazione? I valori esistenti vengono sovrascritti.',imp_conf_replace:'SOSTITUIRE? Utenti, richieste e liste vengono sostituiti del tutto.',imp_done:'Importato:',logs:'Log',clear_cache:'Svuota cache',reindex:'Reindicizza',clear_finished:'Cancella completati',done_word:'Fatto',lbl_jobs:'Richieste',lbl_lib:'Libreria',sec_conn:'Connessioni',reveal:'Mostra in chiaro',tls_hint:'Fornisci certificato + chiave (PEM) — l’app avvia anche un listener HTTPS sulla porta scelta (riavvio necessario).',tls_none:'nessun certificato',tls_expires:'valido fino al',tls_key_note:'chiave privata — mai mostrata',tls_restart:'riavvia il container per attivare',conn_hint:'I campi vuoti usano il valore dell’ambiente (.env). I segreti sono mascherati — lasciare vuoto mantiene il valore.',un_check:'Verifica percorso Usenet',un_hint:'Misura la catena ricerca → categoria → coda → cartella di raccolta senza scaricare nulla. L’ultima riga mostra entrambe le viste della stessa cartella — se divergono, i download finiscono ma non vengono mai raccolti.',un_search:'Ricerca via Prowlarr',un_cat:'Categoria SAB',un_queue:'Coda',un_collect:'Cartella di raccolta',
 profile:'Profilo',display_name:'Nome visualizzato',email:'E-mail',language:'Lingua',design:'Tema',default_design:'Tema predefinito',d_seerr:'Seerr',d_glass:'Vetro',d_clean:'Pulito',avatar:'Avatar',pwebhook:'Webhook Discord personale',change_pw:'Cambia password',cur_pw:'Password attuale',new_pw:'Nuova password',choose_img:'Scegli immagine',saved_ok:'salvato ✓',
 blocklist:'Lista di blocco',add_btn:'Aggiungi',pattern_ph:'Parola chiave/schema nel titolo',
 nav_issues:'🐞 Problemi',nav_messages:'Messaggi',msg_to:'A',msg_none:'Nessun messaggio.',msg_ph:'Scrivi un messaggio …',msg_send:'Invia',msg_hint:'Ctrl+Invio invia',msg_nousers:'Nessun altro utente.',req_for:'Richiesta per',req_self:'me stesso',issues:'Problemi',report_issue:'Segnala problema',issue_msg:'Messaggio',close_btn:'Chiudi',st_open:'aperto',st_closed:'chiuso',submit:'Invia',issue_type:'Tipo',comment_ph:'Scrivi un commento …',comment_send:'Invia',push_enable:'🔔 Attiva push',push_disable:'🔕 Disattiva push',push_unsupported:'Push non disponibile (richiede HTTPS)',push_denied:'Permesso negato',push_on:'Push attivato ✓',push_off:'Push disattivato'
}};
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
function setLang(l){LANG=l;localStorage.setItem('lang',l);applyI18n();
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
const ROUTEN={s:'discover',j:'requests',set:'settings',issues:'issues',msg:'messages',cov:'coverage',lists:'lists'};
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

function show(v){zeige(v);routeSetzen(v,null,false,v==='set'?SETSEC:'',v==='set'?SETSUB:'');}
function zeige(v){cur=v;
 document.getElementById('discview').style.display=v=='s'?'':'none';
 document.getElementById('jobs').style.display=v=='j'?'block':'none';
 document.getElementById('settings').style.display=v=='set'?'block':'none';
 document.getElementById('issues').style.display=v=='issues'?'block':'none';
 document.getElementById('messages').style.display=v=='msg'?'block':'none';
 document.getElementById('coverage').style.display=v=='cov'?'block':'none';
 document.getElementById('lists').style.display=v=='lists'?'block':'none';
 document.getElementById('nS').classList.toggle('on',v=='s');
 document.getElementById('nJ').classList.toggle('on',v=='j');
 document.getElementById('nI').classList.toggle('on',v=='issues');
 let nM=document.getElementById('nM');if(nM)nM.classList.toggle('on',v=='msg');
 document.getElementById('nSet').classList.toggle('on',v=='set');
 if(v=='j')loadJobs();if(v=='set')openSettingsView();
 if(v=='issues'){loadIssues(window._ipref);window._ipref=null;}
 let nC=document.getElementById('nC');if(nC)nC.classList.toggle('on',v=='cov');
 if(v=='msg')loadMessages();if(v=='cov')loadCoverage();if(v=='lists')loadLists();}
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
  (users.length?`<div class=frow><label style="min-width:auto">${t('msg_to')}</label><select id=msgsel onchange="msgWith=this.value;loadMessages()">${opts}</select></div>
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
  <div class=frow><input id=iplat placeholder="Plattform" style="flex:0 0 140px" value="${((pref&&pref.platform)||'').replace(/"/g,'&quot;')}"><select id=ityp>${types.map(x=>'<option>'+x+'</option>').join('')}</select></div>
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
 let z=kartenZustand(it);
 // Anzeigename statt rohem Slug (#211): die Karte sagte `ngc` statt „GameCube". Die
 // Namen kommen aus /api/platforms, dieselbe Quelle wie die Filterleiste — kein zweiter
 // Datenbestand, der auseinanderlaufen kann. `?` bleibt `?`, das ist ein echter Fall.
 let plat=plattformMarke(it.platform_slug);
 c.innerHTML=`<div class=cover style="${cov}"><span class=badge>${plat}</span><span class=src>${src}</span>`+
  (z?`<span class="zust ${z.cls}" title="${z.text}">${z.zeichen} ${z.text}</span>`:'')+`</div>
  <div class=body><div class=t>${FAVS.has(norm(it.title||''))?'<span class=favmark title="'+t('favourite')+'">♥</span> ':''}${it.title.replace(/</g,'&lt;')}</div><div class=meta>${sz(it.size)}${settag}</div><div class=act></div></div>`;
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
    bar.innerHTML=`<div class=frow style="margin-bottom:8px"><label style="min-width:auto;color:#8b929e;font-size:12px">${t('req_for')}</label><select id=reqforsel onchange="window.reqFor=this.value"><option value="">${t('req_self')}</option>${names.map(u=>`<option value="${u}">${u.replace(/</g,'&lt;')}</option>`).join('')}</select></div>`;}}catch(e){}}
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
   <span class=meta style="margin-left:8px">${t('stream_single')}</span>`;
 }else if(d.reason==='busy'){
  box.innerHTML=`<span class=meta style="color:#d29922">📺 ${t('stream_busy').replace('{u}',(d.busy_user||'?')).replace('{g}',(d.busy_with||'?'))}</span>
   <button onclick="stopStream()" style="margin-left:8px;background:#2a2f37;border:none;color:#e6e8ec;padding:4px 10px;border-radius:6px;cursor:pointer">${t('stream_stop')}</button>`;
 }else{
  box.innerHTML=`<span class=meta>📺 ${t(d.reason==='not_in_library'?'stream_not_in_lib':'stream_no')}</span>`;}}
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
 if(d.launch_error){let s=document.createElement('div');s.className='meta';
  s.style.cssText='margin-top:6px;color:#d29922;font-size:11px';
  s.textContent=d.launch_error;btn.parentNode.appendChild(s);}
 window.open(d.url,'_blank','noopener');}
async function stopStream(){await fetch('/api/stream/stop',{method:'POST'});closeModal();}
// Ohne Argument ist Schliessen eine Navigation: zurueck zur Ansicht, aus der das Fenster
// geoeffnet wurde. `ausRoute` schliesst nur die Anzeige — dann hat der Verlauf sich
// bereits bewegt und ein weiterer history.back() wuerde aus der App hinausfuehren. (#194)
function closeModal(ausRoute){
 document.getElementById('modal').style.display='none';
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
let JOBGRP='';   // '' = alle; sonst aktiv|erledigt|fehler
async function loadJobs(){let r=await fetch('/api/jobs');let d=await r.json();let j=document.getElementById('jobs');
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
    right+=`<button onclick="retryJob('${o.id}')" style="background:#2a2f37;border:none;color:#fff;padding:5px 10px;border-radius:6px;cursor:pointer;margin-left:8px" title="${t('retry')}">↻ ${t('retry')}</button>`;}
  let dt=o.created?new Date(o.created*1000).toLocaleString():'';
  // Gelieferte Fassung im Verlauf zeigen — damit eine Falschlieferung belegbar ist. (#77)
  let vl=o.variant_label?` · 🏷 ${o.variant_label.replace(/</g,'&lt;')}`:'';
  e.innerHTML=`<div><div>${o.title.replace(/</g,'&lt;')}</div><div class=meta style="color:#8b929e;font-size:11px">👤 <b style="color:#b9c0cc">${(o.user||'—').replace(/</g,'&lt;')}</b> · ${o.platform} · ${o.source}${vl}${dt?' · '+dt:''} · ${o.msg||''}</div></div><div>${right}</div>`;
  j.appendChild(e);});}
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
   window._who=`<img src="${d.avatar||defAvatar(nm)}">`+nm.replace(/</g,'&lt;')+' <span style="opacity:.7">▾</span>';}
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
       ['ra','RetroAchievements',d=>({da:false,an:false})],
       ['jd','JDownloader',     d=>({da:!!(d.connections||{}).jd_dl_base,an:!!(d.connections||{}).jd_dl_base})],
       ['catalog',null,         d=>({da:!!(d.connections||{}).catalog_urls,an:!!(d.connections||{}).catalog_urls}),'cat_title'],
       ['stream',null,          d=>({da:!!(d.connections||{}).stream_url,an:!!(d.connections||{}).stream_url}),'stream_title']]};
function subLabel(e){return e[3]?t(e[3]):e[1];}
function openSettingsView(){
 let secs=[['general',t('sec_general')],['notif',t('sec_notif')],['conn',t('sec_conn')],['users',t('sec_users')],['blocklist',t('blocklist')],['services',t('sec_services')],['maint',t('sec_maint')],['tls','HTTPS'],['about',t('sec_about')]];
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
 ({general:secGeneral,notif:secNotif,conn:secConn,users:secUsers,blocklist:secBlocklist,services:secServices,maint:secMaint,tls:secTls,about:secAbout}[sec]||secGeneral)(c);}
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
  <div class=meta style="margin-top:14px;line-height:1.5">${t('un_hint')}</div>
  <div class=frow style="margin-top:6px"><button onclick="unCheck()" style="background:#2a2f37">${t('un_check')}</button></div>
  <div id=unres style="margin-top:8px"></div>`,
  prow:()=>`<h3>Prowlarr</h3>${fld('prow_url','URL')}${fld('prow_apikey','API-Key',1)}${fld('prow_cats','Kategorien / categories')}${fuss}`,
  igdb:()=>`<h3>IGDB</h3>${fld('igdb_id','Client-ID')}${fld('igdb_secret','Client-Secret',1)}${fuss}`,
  scraper:()=>`<h3>${t('conn_scraper')}</h3>${fld('sgdb_key','SteamGridDB-Key',1)}${fld('ss_user','ScreenScraper-User')}${fld('ss_pass','ScreenScraper-Passwort',1)}${fuss}`,
  romm:()=>`<h3>RomM</h3>${fld('romm_url','URL')}${fld('romm_user','User')}${fld('romm_pass','Passwort / password',1)}${fuss}`,
  ra:()=>`<h3>RetroAchievements</h3>${fld('ra_key','API-Key',1)}
   <div class=frow><span class=meta id=rastat style="flex:1">…</span>
    <button type=button onclick="raRefresh()" style="background:#2a2f37">${t('ra_refresh')}</button></div>${fuss}`,
  jd:()=>`<h3>JDownloader</h3><div class=meta style="font-size:11px;margin-bottom:4px">${t('jd_hint')}</div>
   ${fld('jd_watch',t('jd_watch'))}${fld('jd_out',t('jd_out'))}${fld('jd_dl_base',t('jd_base'))}${fuss}`,
  catalog:()=>`<h3>${t('cat_title')}</h3><div class=meta style="font-size:11px;margin-bottom:4px">${t('cat_hint')}</div>
   <div class=frow><label style="min-width:150px">${t('cat_urls')}</label>
    <textarea id=c_catalog_urls style="flex:1;min-height:60px;background:#0b0d10;border:1px solid #2c323b;color:#e6e8ec;padding:6px;border-radius:6px;font-family:ui-monospace,monospace;font-size:11px">${(vals['catalog_urls']||'').replace(/</g,'&lt;')}</textarea></div>
   <div class=frow><span class=meta id=catstat style="flex:1">…</span>
    <button type=button onclick="catRefresh()" style="background:#2a2f37">${t('cat_refresh')}</button></div>${fuss}`,
  stream:()=>`<h3>${t('stream_title')}</h3><div class=meta style="font-size:11px;margin-bottom:4px">${t('stream_hint')}</div>
   ${fld('stream_url',t('stream_url_l'))}${fld('stream_launch',t('stream_launch_l'),1)}
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
   let rb=e.can_rollback?` <a href="#" onclick="emuRollback('${e.dir}');return false" title="${(e.previous||'').replace(/"/g,'')}" style="color:#d29922">↩</a>`:'';
   return '<b>'+e.name+'</b>'+v+rb;}).join(' · ')
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
async function emuUpdate(){let el=document.getElementById('emustat');el.textContent='…';
 let r=await fetch('/api/stream/emulators/update',{method:'POST'});
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
const CONN_ALL=['sab_url','sab_apikey','sab_cat','prow_url','prow_apikey','prow_cats','igdb_id','igdb_secret','sgdb_key','ss_user','ss_pass','romm_url','romm_user','romm_pass','jd_watch','jd_out','jd_dl_base','ra_key','catalog_urls','stream_url','stream_launch'];
const CONN_SEC=['sab_apikey','prow_apikey','igdb_secret','sgdb_key','ss_pass','romm_pass'];
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
async function unCheck(){let b=document.getElementById('unres');b.textContent='…';
 let d={};try{d=await(await fetch('/api/usenet/check')).json();}catch(e){b.textContent=t('st_error');return;}
 b.innerHTML=((d||{}).steps||[]).map(x=>`<div class=meta>${x.ok?'✅':'❌'} <b>${t(UN_NAME[x.step]||x.step)}</b> — ${(x.info||'').replace(/</g,'&lt;')}</div>`).join('')||`<div class=meta>${t('st_error')}</div>`;}
async function secMaint(c){
 c.innerHTML=`<h3>${t('sec_maint')}</h3><div id=mstats class=meta>…</div>
  <div style="margin:10px 0;display:flex;gap:8px;flex-wrap:wrap">
   <button onclick="admCache()">${t('clear_cache')}</button>
   <button onclick="admReindex()">${t('reindex')}</button>
   <button onclick="admClearJobs()">${t('clear_finished')}</button>
   <button onclick="loadLogs()">${t('refresh')}</button>
   <span id=mmsg class=meta></span></div>
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
 loadMStats();loadLogs();}
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
async function admClearJobs(){let r=await(await fetch('/api/jobs/clear-finished',{method:'POST'})).json();document.getElementById('mmsg').textContent=t('done_word')+' ('+(r.removed||0)+')';loadMStats();}
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
async function secAbout(c){
 let st={};try{st=await(await fetch('/api/admin/stats')).json();}catch(e){}
 let ver={};try{ver=await(await fetch('/api/version?check=1')).json();}catch(e){}
 let repo='https://github.com/Sparxx947/romseerr';
 let build=[ver.commit?ver.commit.slice(0,7):'',ver.built_at||''].filter(Boolean).join(' · ');
 let upd=ver.update_available?` <a href="${repo}/releases/latest" target=_blank style="color:#5b8cff">${t('upd_avail')} ${ver.latest}</a>`
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
   🔗 <a href="${repo}" target=_blank style="color:#5b8cff">GitHub-Repo</a><br>
   📖 <a href="${repo}/wiki" target=_blank style="color:#5b8cff">Wiki</a> · <a href="/api/docs" target=_blank style="color:#5b8cff">API-Doku</a> · <a href="${repo}/blob/main/CHANGELOG.md" target=_blank style="color:#5b8cff">Changelog</a><br>
   🐞 <a href="${repo}/issues" target=_blank style="color:#5b8cff">Issues melden</a> · 🔒 <a href="${repo}/security/advisories/new" target=_blank style="color:#5b8cff">Sicherheitslücke melden</a>
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
async function retryJob(id){await fetch('/api/jobs/'+id+'/retry',{method:'POST'});loadJobs();}
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
