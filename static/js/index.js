const I18N={de:{
 nav_discover:'🔍 Entdecken',nav_requests:'📥 Anfragen',nav_users:'👤 Benutzer',nav_settings:'⚙️ Einstellungen',logout:'🚪 Abmelden',
 search_ph:'Spiel suchen … (Enter)',platforms:'Plattformen',all:'Alle',selected:'gewählt',
 hint_type:'Tippe einen Titel und drücke Enter.',loading_home:'Lade Startseite …',popular_on:'Beliebt auf',click_search:'klick zum Suchen',
 searching:'Suche läuft …',no_results:'Keine Treffer.',results:'Treffer',in_library:'✓ in Bibliothek',download:'⬇ Download',requested:'✓ angefragt',collection:'Sammlung',
 versions:'Versionen / Quellen',files:'Dateien',no_desc:'Keine Beschreibung verfügbar.',screenshots:'Screenshots',similar:'Ähnliche Spiele',series:'Reihe',because_you:'Weil du angefragt hast:',
 no_requests:'Noch keine Anfragen.',approve:'Freigeben',deny:'Ablehnen',retry:'Erneut',reset:'Alle zurücksetzen',req_all:'Alle anfragen',flt_user:'Nutzer',flt_all:'Alle',wishlist:'Wunschliste',nav_coverage:'Abdeckung',emu_rb_confirm:'{n} auf die vorherige Fassung zurücksetzen?',emu_rb_failed:'Zurücksetzen fehlgeschlagen',emu_update:'Emulatoren aktualisieren',emu_nohost:'kein Streaming-Host erreichbar',emu_nolauncher:'kein Start-Dienst hinterlegt',emu_unreachable:'Start-Dienst nicht erreichbar',emu_running:'Aktualisierung läuft …',emu_none:'keine Emulatoren installiert',emu_ok:'zuletzt erfolgreich',emu_failed:'zuletzt fehlgeschlagen',stream:'Streamen',stream_single:'Einzelplatz — eine Sitzung gleichzeitig',stream_busy:'Belegt: {u} spielt gerade {g}',stream_stop:'Sitzung beenden',stream_not_in_lib:'Zum Streamen muss der Titel in der Bibliothek liegen.',stream_no:'Streamen gerade nicht möglich.',stream_running:'▶ läuft — Fenster geöffnet',stream_manual:'Desktop geöffnet — Titel dort starten',stream_title:'Streaming-Host',stream_hint:'Für Plattformen, die der Browser nicht emulieren kann (PS2, GameCube, Wii, Switch). Der Emulator läuft auf dem Host, der Browser bekommt Bild und Ton. Ohne Start-Dienst öffnet Romseerr nur den Desktop.',stream_url_l:'Browser-URL des Hosts',stream_launch_l:'Start-Dienst (optional)',sec_outbound:'Ausgehende Anfragen',outbound_hint:'Webhook- und Katalog-URLs setzt der Nutzer. Standardmäßig lehnt Romseerr Ziele im privaten Netz, auf Loopback und Link-Local ab — sonst könnte jeder angemeldete Nutzer den Server auf interne Adressen schicken. Wer sein Benachrichtigungsziel im selben Netz betreibt, muss das hier ausdrücklich erlauben.',outbound_allow:'Ziele im privaten Netz erlauben',play:'Im Browser spielen',play_no_romm:'Spielen nicht möglich — RomM ist nicht verbunden.',play_no_core:'Diese Plattform lässt sich im Browser nicht emulieren.',play_not_in_lib:'Zum Spielen muss der Titel in der Bibliothek liegen.',play_too_large:'Zu groß für den Browser (Grenze {mb} MB).',play_no_title:'Kein Titel.',play_bios:'braucht BIOS',play_romset:'Arcade: nur mit passendem Romset',cat_title:'Filehoster-Kataloge (experimentell)',cat_hint:'Katalog-JSON-Quellen, eine URL je Zeile. Bewusst NICHT mitgeliefert — die Quellen bestimmt der Betreiber. Format: {name, downloads:[{title,uris,uploadDate,fileSize}]}.',cat_urls:'Quell-URLs',cat_refresh:'Jetzt holen',cat_none:'keine Quelle hinterlegt — der Filehoster-Weg ist inaktiv',cat_items:'Einträge insgesamt',jd_hint:'Drei Sichten auf dieselbe Übergabe: die ersten beiden sieht Romseerr, die dritte JDownloader. Leer = Standard.',jd_watch:'Watch-Ordner (Romseerr schreibt)',jd_out:'Fertig-Ordner (Romseerr liest)',jd_base:'Download-Basis (JDownloader-Sicht)',var_prefs:'Fassungen (Region/Sprache)',var_region_order:'Regionsreihenfolge — die Reihenfolge ist die Vorliebe',var_lang:'Bevorzugte Sprache',var_prerelease:'Beta/Prototyp/Demo zulassen',var_unspec:'unspezifiziert',var_preferred:'bevorzugt',var_hint:'Instanzweiter Rückfall für Nutzer, die selbst nichts eingestellt haben. Region ändert Inhalt (Sprache, Schwierigkeit, Zensur, 50/60 Hz) — das ist keine Qualitätsleiter, deshalb wird nach dieser Reihenfolge gewählt und nicht sortiert.',var_of:'Fassung',ra_achievements:'Achievements',ra_points:'Punkte',ra_earned:'erreicht',ra_user:'RetroAchievements-Konto (optional)',ra_refresh:'Sets holen',ra_sets:'Sets',ra_nokey:'kein API-Key hinterlegt',ra_unmapped:'ohne Konsolen-Zuordnung',ra_only:'nur mit Achievements',cov_of:'von',cov_src:'Quelle',cov_asof:'Stand',cov_files:'Dateien',cov_missing:'fehlende Titel',cov_refresh:'Katalog aktualisieren',cov_nosnap:'keine Momentaufnahme — Katalog noch nicht geholt',cov_nosource:'keine Katalogquelle für diese Plattform',cov_basis:'Grundlage ist eine Momentaufnahme aus {src} (max. {max} Titel je Plattform). Metadatensätze sind sich uneins, was als eigener Titel zählt — die Prozentzahl ist eine Orientierung, kein Messwert.',cov_search:'Suchen',cov_none:'Nichts fehlt (oder kein Katalog).',cov_filter:'Filtern …',cov_filter_do:'Filtern',cov_wish_sel:'Auswahl auf die Wunschliste',wl_import:'Import',wl_imp_hint:'Liste einfügen oder Datei wählen (TXT/CSV) — ein Titel je Zeile, optional Titel;Plattform. Nichts wird geschrieben, bevor du die Vorschau bestätigst.',wl_imp_example:'Beispieldatei herunterladen',wl_imp_ph:'Chrono Trigger\nSuper Metroid;snes',wl_imp_preview:'Vorschau',wl_imp_apply:'Übernehmen',wl_imp_none:'Nichts ausgewählt.',wl_imp_done:'{a} übernommen, {s} übersprungen.',wl_imp_trunc:'Nur die ersten {n} Zeilen werden geprüft.',wl_imp_toobig:'Datei zu groß (max. 200 kB).',wl_imp_nocheck:'Ohne IGDB-Zugang kein Katalogabgleich — Einträge werden ungeprüft übernommen.',wl_s_matched:'getroffen',wl_s_ambiguous:'mehrdeutig',wl_s_notfound:'nicht gefunden',wl_s_duplicate:'schon gemerkt',wl_s_inlib:'schon vorhanden',wl_s_unverified:'ungeprüft',add_wishlist:'⭐ Merken',wl_added:'⭐ gemerkt',wl_empty:'Wunschliste leer.',wl_remove:'Entfernen',
 users:'Benutzer',new_user:'Neuen Benutzer anlegen',create:'Anlegen',del:'Löschen',autoapprove:'Auto-Freigabe',role_user:'Nutzer',role_admin:'Admin',username:'Benutzername',password:'Passwort',
 notif_discord:'Benachrichtigungen — Discord',active:'aktiv',test:'Test',save:'Speichern',saved:'gespeichert ✓',test_sent:'Test gesendet ✓',webhook_ph:'Discord Webhook-URL',
 st_pending:'⏳ Wartet auf Freigabe',st_queued:'Angefragt',st_downloading:'Lädt…',st_importing:'Wird verarbeitet',st_done:'✅ Verfügbar',st_error:'Fehler',st_denied:'Abgelehnt',st_exists:'vorhanden',
 settings:'Einstellungen',sec_general:'Allgemein',sec_notif:'Benachrichtigungen',sec_users:'Benutzer',sec_services:'Dienste',sec_about:'Über',app_name:'App-Name',default_lang:'Standardsprache',refresh:'Aktualisieren',version:'Version',about_build:'Build',upd_avail:'Update verfügbar:',upd_current:'aktuell',about_txt:'Selbstgebauter Seerr-Klon für ROMs.',wiz_welcome:'Willkommen bei Romseerr',wiz_welcome_txt:'Dieser Assistent verbindet dich Schritt für Schritt mit den Diensten des Stacks (SABnzbd, Prowlarr, IGDB, RomM). Jeden Schritt kannst du testen oder überspringen.',wiz_done:'Fertig!',wiz_done_txt:'Die Grundkonfiguration steht. Alles lässt sich später unter Einstellungen → Verbindungen anpassen.',wiz_next:'Weiter',wiz_back:'Zurück',wiz_skip:'Überspringen',wiz_finish:'Loslegen',wiz_step:'Schritt',wiz_reopen:'Assistent erneut öffnen',about_lib:'Bibliothek',about_titles:'Titel',about_platforms:'Plattformen',about_jobs:'Anfragen',about_active:'aktiv',about_links:'Links',about_feat:'Funktionen',about_feat_txt:'Suche über Archive.org + Usenet, Dedup, Discover, Anfragen mit Freigabe, Benutzer & Rechte, Kontingente, Benachrichtigungen (Discord/Telegram/E-Mail/Web-Push), Probleme, PWA, API.',about_stack:'Stack',about_stack_txt:'Orchestriert Prowlarr, SABnzbd, JDownloader und RomM. Verbindungen in den Einstellungen konfigurierbar.',about_license:'Lizenz: MIT',sec_maint:'Logs & Wartung',exp_title:'Export / Import',exp_hint:'Sichert Einstellungen, Benutzer & Rechte, Anfragen und Wunschlisten als JSON. Ohne Passphrase bleiben Geheimnisse (Kennwörter, API-Keys, Webhook-URLs) AUSSEN VOR — mit Passphrase werden sie verschlüsselt beigelegt. Dieselbe Passphrase wird beim Import gebraucht.',exp_pass:'Passphrase',exp_pass_ph:'leer = ohne Geheimnisse',exp_do:'Exportieren',exp_merge:'Zusammenführen',exp_replace:'Ersetzen',imp_do:'Importieren',exp_done_plain:'Exportiert (ohne Geheimnisse).',exp_done_enc:'Exportiert (Geheimnisse verschlüsselt).',imp_nofile:'Keine Datei gewählt.',imp_badjson:'Datei ist kein gültiges JSON.',imp_conf_merge:'Import zusammenführen? Bestehende Werte werden überschrieben, nicht genannte bleiben.',imp_conf_replace:'ERSETZEN? Benutzer, Anfragen und Wunschlisten werden vollständig durch die Datei ersetzt.',imp_done:'Importiert:',logs:'Protokoll',clear_cache:'Cache leeren',reindex:'Neu indexieren',clear_finished:'Fertige entfernen',done_word:'Erledigt',lbl_jobs:'Anfragen',lbl_lib:'Bibliothek',sec_conn:'Verbindungen',reveal:'Klartext anzeigen',tls_hint:'Cert + Schlüssel (PEM) hinterlegen — die App startet dann zusätzlich einen HTTPS-Listener auf dem gewählten Port (Neustart nötig). Für Web-Push/PWA ohne separaten Reverse-Proxy.',tls_none:'kein Zertifikat hinterlegt',tls_expires:'gültig bis',tls_key_note:'privater Schlüssel — wird nie angezeigt',tls_restart:'Container neu starten zum Aktivieren',conn_hint:'Leere Felder nutzen den Wert aus der Umgebung (.env). Secrets sind maskiert — leer lassen behält den bestehenden Wert.',
 profile:'Profil',display_name:'Anzeigename',email:'E-Mail',language:'Sprache',design:'Design',default_design:'Standard-Design',d_seerr:'Seerr',d_glass:'Glas',d_clean:'Klar',avatar:'Avatar',pwebhook:'Persönlicher Discord-Webhook',change_pw:'Passwort ändern',cur_pw:'Aktuelles Passwort',new_pw:'Neues Passwort',choose_img:'Bild wählen',saved_ok:'gespeichert ✓',
 blocklist:'Sperrliste',add_btn:'Hinzufügen',pattern_ph:'Stichwort/Muster im Titel',
 nav_issues:'🐞 Probleme',nav_messages:'Nachrichten',msg_to:'An',msg_none:'Noch keine Nachrichten.',msg_ph:'Nachricht schreiben …',msg_send:'Senden',msg_hint:'Strg+Enter sendet',msg_nousers:'Keine anderen Benutzer.',req_for:'Anfrage für',req_self:'mich selbst',issues:'Probleme',report_issue:'Problem melden',issue_msg:'Beschreibung',close_btn:'Schließen',st_open:'offen',st_closed:'geschlossen',submit:'Absenden',issue_type:'Art',comment_ph:'Kommentar schreiben …',comment_send:'Senden',push_enable:'🔔 Push aktivieren',push_disable:'🔕 Push deaktivieren',push_unsupported:'Push nicht verfügbar (HTTPS nötig)',push_denied:'Erlaubnis verweigert',push_on:'Push aktiviert ✓',push_off:'Push deaktiviert'
},en:{
 nav_discover:'🔍 Discover',nav_requests:'📥 Requests',nav_users:'👤 Users',nav_settings:'⚙️ Settings',logout:'🚪 Sign out',
 search_ph:'Search a game … (Enter)',platforms:'Platforms',all:'All',selected:'selected',
 hint_type:'Type a title and press Enter.',loading_home:'Loading home …',popular_on:'Popular on',click_search:'click to search',
 searching:'Searching …',no_results:'No results.',results:'results',in_library:'✓ in library',download:'⬇ Download',requested:'✓ requested',collection:'Collection',
 versions:'Versions / sources',files:'Files',no_desc:'No description available.',screenshots:'Screenshots',similar:'Similar games',series:'Series',because_you:'Because you requested:',
 no_requests:'No requests yet.',approve:'Approve',deny:'Deny',retry:'Retry',reset:'Reset all',req_all:'Request all',flt_user:'User',flt_all:'All',wishlist:'Wishlist',nav_coverage:'Coverage',emu_rb_confirm:'Roll {n} back to the previous build?',emu_rb_failed:'rollback failed',emu_update:'Update emulators',emu_nohost:'no streaming host reachable',emu_nolauncher:'no launch service configured',emu_unreachable:'launch service unreachable',emu_running:'update running …',emu_none:'no emulators installed',emu_ok:'last run succeeded',emu_failed:'last run failed',stream:'Stream',stream_single:'single seat — one session at a time',stream_busy:'In use: {u} is playing {g}',stream_stop:'End session',stream_not_in_lib:'The title must be in the library to stream it.',stream_no:'Streaming not available right now.',stream_running:'▶ running — window opened',stream_manual:'desktop opened — start the title there',stream_title:'Streaming host',stream_hint:'For platforms the browser cannot emulate (PS2, GameCube, Wii, Switch). The emulator runs on the host; the browser receives video and audio. Without a launch service Romseerr only opens the desktop.',stream_url_l:'Browser URL of the host',stream_launch_l:'Launch service (optional)',sec_outbound:'Outbound requests',outbound_hint:'Webhook and catalogue URLs come from users. By default Romseerr refuses private, loopback and link-local targets — otherwise any logged-in user could point the server at internal addresses. If your notification target lives on the same network, allow it explicitly here.',outbound_allow:'Allow targets in private networks',play:'Play in browser',play_no_romm:'Cannot play — RomM is not connected.',play_no_core:'This platform cannot be emulated in the browser.',play_not_in_lib:'The title must be in the library to play it.',play_too_large:'Too large for the browser (limit {mb} MB).',play_no_title:'No title.',play_bios:'needs BIOS',play_romset:'arcade: only with a matching romset',cat_title:'Filehoster catalogues (experimental)',cat_hint:'Catalogue JSON sources, one URL per line. Deliberately not shipped — the operator supplies the sources. Format: {name, downloads:[{title,uris,uploadDate,fileSize}]}.',cat_urls:'Source URLs',cat_refresh:'Fetch now',cat_none:'no source configured — the filehoster path is inactive',cat_items:'entries in total',jd_hint:'Three views of the same handover: Romseerr sees the first two, JDownloader the third. Empty = default.',jd_watch:'Watch folder (Romseerr writes)',jd_out:'Finished folder (Romseerr reads)',jd_base:'Download base (JDownloader view)',var_prefs:'Release variants (region/language)',var_region_order:'Region order — the order is the preference',var_lang:'Preferred language',var_prerelease:'Accept beta/prototype/demo',var_unspec:'unspecified',var_preferred:'preferred',var_hint:'Instance-wide fallback for users who set nothing themselves. Region changes content (language, difficulty, censorship, 50/60 Hz) — that is not a quality ladder, so candidates follow this order rather than being sorted.',var_of:'Variant',ra_achievements:'achievements',ra_points:'points',ra_earned:'earned',ra_user:'RetroAchievements account (optional)',ra_refresh:'Fetch sets',ra_sets:'sets',ra_nokey:'no API key stored',ra_unmapped:'no console mapping',ra_only:'with achievements only',cov_of:'of',cov_src:'Source',cov_asof:'as of',cov_files:'files',cov_missing:'missing titles',cov_refresh:'Refresh catalogue',cov_nosnap:'no snapshot — catalogue not fetched yet',cov_nosource:'no catalogue source for this platform',cov_basis:'Based on a snapshot from {src} (max {max} titles per platform). Metadata sets disagree about what counts as a distinct title — the percentage is an orientation, not a measurement.',cov_search:'Search',cov_none:'Nothing missing (or no catalogue).',cov_filter:'Filter …',cov_filter_do:'Filter',cov_wish_sel:'Selection to wishlist',wl_import:'Import',wl_imp_hint:'Paste a list or pick a file (TXT/CSV) — one title per line, optionally title;platform. Nothing is written until you confirm the preview.',wl_imp_example:'Download example file',wl_imp_ph:'Chrono Trigger\nSuper Metroid;snes',wl_imp_preview:'Preview',wl_imp_apply:'Import',wl_imp_none:'Nothing selected.',wl_imp_done:'{a} imported, {s} skipped.',wl_imp_trunc:'Only the first {n} lines are checked.',wl_imp_toobig:'File too large (max 200 kB).',wl_imp_nocheck:'No IGDB credentials — no catalogue check; entries are imported unverified.',wl_s_matched:'matched',wl_s_ambiguous:'ambiguous',wl_s_notfound:'not found',wl_s_duplicate:'already listed',wl_s_inlib:'already in library',wl_s_unverified:'unverified',add_wishlist:'⭐ Watch',wl_added:'⭐ watched',wl_empty:'Wishlist empty.',wl_remove:'Remove',
 users:'Users',new_user:'Create new user',create:'Create',del:'Delete',autoapprove:'Auto-approve',role_user:'User',role_admin:'Admin',username:'Username',password:'Password',
 notif_discord:'Notifications — Discord',active:'enabled',test:'Test',save:'Save',saved:'saved ✓',test_sent:'test sent ✓',webhook_ph:'Discord webhook URL',
 st_pending:'⏳ Awaiting approval',st_queued:'Requested',st_downloading:'Downloading…',st_importing:'Processing',st_done:'✅ Available',st_error:'Error',st_denied:'Denied',st_exists:'in library',
 settings:'Settings',sec_general:'General',sec_notif:'Notifications',sec_users:'Users',sec_services:'Services',sec_about:'About',app_name:'App name',default_lang:'Default language',refresh:'Refresh',version:'Version',about_build:'Build',upd_avail:'Update available:',upd_current:'up to date',about_txt:'Self-built Seerr clone for ROMs.',wiz_welcome:'Welcome to Romseerr',wiz_welcome_txt:'This wizard connects you to the stack services (SABnzbd, Prowlarr, IGDB, RomM) step by step. You can test or skip each step.',wiz_done:'All set!',wiz_done_txt:'Basic configuration is done. You can adjust everything later under Settings → Connections.',wiz_next:'Next',wiz_back:'Back',wiz_skip:'Skip',wiz_finish:'Get started',wiz_step:'Step',wiz_reopen:'Reopen wizard',about_lib:'Library',about_titles:'titles',about_platforms:'platforms',about_jobs:'Requests',about_active:'active',about_links:'Links',about_feat:'Features',about_feat_txt:'Search across Archive.org + Usenet, dedup, discover, requests with approval, users & permissions, quotas, notifications (Discord/Telegram/email/web push), issues, PWA, API.',about_stack:'Stack',about_stack_txt:'Orchestrates Prowlarr, SABnzbd, JDownloader and RomM. Connections configurable under Settings.',about_license:'License: MIT',sec_maint:'Logs & maintenance',exp_title:'Export / import',exp_hint:'Saves settings, users & permissions, requests and wishlists as JSON. Without a passphrase, secrets (passwords, API keys, webhook URLs) are LEFT OUT — with one they are attached encrypted. The same passphrase is needed on import.',exp_pass:'Passphrase',exp_pass_ph:'empty = without secrets',exp_do:'Export',exp_merge:'Merge',exp_replace:'Replace',imp_do:'Import',exp_done_plain:'Exported (without secrets).',exp_done_enc:'Exported (secrets encrypted).',imp_nofile:'No file selected.',imp_badjson:'File is not valid JSON.',imp_conf_merge:'Merge this import? Existing values are overwritten, anything not mentioned stays.',imp_conf_replace:'REPLACE? Users, requests and wishlists are fully replaced by the file.',imp_done:'Imported:',logs:'Log',clear_cache:'Clear cache',reindex:'Reindex',clear_finished:'Clear finished',done_word:'Done',lbl_jobs:'Requests',lbl_lib:'Library',sec_conn:'Connections',reveal:'Show in clear text',tls_hint:'Provide cert + key (PEM) — the app then also starts an HTTPS listener on the chosen port (restart required). For web push/PWA without a separate reverse proxy.',tls_none:'no certificate stored',tls_expires:'valid until',tls_key_note:'private key — never shown',tls_restart:'restart the container to activate',conn_hint:'Empty fields fall back to the environment (.env). Secrets are masked — leave blank to keep the current value.',
 profile:'Profile',display_name:'Display name',email:'Email',language:'Language',design:'Design',default_design:'Default design',d_seerr:'Seerr',d_glass:'Glass',d_clean:'Clean',avatar:'Avatar',pwebhook:'Personal Discord webhook',change_pw:'Change password',cur_pw:'Current password',new_pw:'New password',choose_img:'Choose image',saved_ok:'saved ✓',
 blocklist:'Blocklist',add_btn:'Add',pattern_ph:'Keyword/pattern in title',
 nav_issues:'🐞 Issues',nav_messages:'Messages',msg_to:'To',msg_none:'No messages yet.',msg_ph:'Write a message …',msg_send:'Send',msg_hint:'Ctrl+Enter sends',msg_nousers:'No other users.',req_for:'Request for',req_self:'myself',issues:'Issues',report_issue:'Report issue',issue_msg:'Message',close_btn:'Close',st_open:'open',st_closed:'closed',submit:'Submit',issue_type:'Type',comment_ph:'Write a comment …',comment_send:'Send',push_enable:'🔔 Enable push',push_disable:'🔕 Disable push',push_unsupported:'Push unavailable (needs HTTPS)',push_denied:'Permission denied',push_on:'Push enabled ✓',push_off:'Push disabled'
},fr:{
 nav_discover:'🔍 Découvrir',nav_requests:'📥 Demandes',nav_users:'👤 Utilisateurs',nav_settings:'⚙️ Paramètres',logout:'🚪 Déconnexion',
 search_ph:'Rechercher un jeu … (Entrée)',platforms:'Plateformes',all:'Toutes',selected:'sélectionné',
 hint_type:'Saisissez un titre et appuyez sur Entrée.',loading_home:'Chargement …',popular_on:'Populaire sur',click_search:'cliquer pour rechercher',
 searching:'Recherche …',no_results:'Aucun résultat.',results:'résultats',in_library:'✓ dans la bibliothèque',download:'⬇ Télécharger',requested:'✓ demandé',collection:'Collection',
 versions:'Versions / sources',files:'Fichiers',no_desc:'Aucune description disponible.',screenshots:'Captures',similar:'Jeux similaires',series:'Série',because_you:'Parce que vous avez demandé :',
 no_requests:'Aucune demande.',approve:'Approuver',deny:'Refuser',retry:'Réessayer',reset:'Tout réinitialiser',req_all:'Tout demander',flt_user:'Utilisateur',flt_all:'Tous',wishlist:'Liste de souhaits',nav_coverage:'Couverture',emu_rb_confirm:'Revenir à la version précédente de {n} ?',emu_rb_failed:'retour échoué',emu_update:'Mettre à jour les émulateurs',emu_nohost:'aucun hôte de diffusion',emu_nolauncher:'aucun service de lancement',emu_unreachable:'service injoignable',emu_running:'mise à jour en cours …',emu_none:'aucun émulateur installé',emu_ok:'dernier essai réussi',emu_failed:'dernier essai échoué',stream:'Diffuser',stream_single:'place unique — une session à la fois',stream_busy:'Occupé : {u} joue à {g}',stream_stop:'Terminer la session',stream_not_in_lib:'Le titre doit être dans la bibliothèque.',stream_no:'Diffusion indisponible.',stream_running:'▶ en cours — fenêtre ouverte',stream_manual:'bureau ouvert — lancez le titre là-bas',stream_title:'Hôte de diffusion',stream_hint:'Pour les plateformes que le navigateur ne peut pas émuler (PS2, GameCube, Wii, Switch).',stream_url_l:'URL navigateur de l’hôte',stream_launch_l:'Service de lancement (optionnel)',sec_outbound:'Requêtes sortantes',outbound_hint:'Les URLs de webhook viennent des utilisateurs. Par défaut, les cibles privées, loopback et link-local sont refusées. Autorisez-les explicitement si votre destination est sur le même réseau.',outbound_allow:'Autoriser les cibles en réseau privé',play:'Jouer dans le navigateur',play_no_romm:'Impossible — RomM n’est pas connecté.',play_no_core:'Cette plateforme ne peut pas être émulée dans le navigateur.',play_not_in_lib:'Le titre doit être dans la bibliothèque.',play_too_large:'Trop volumineux pour le navigateur (limite {mb} Mo).',play_no_title:'Aucun titre.',play_bios:'nécessite un BIOS',play_romset:'arcade : romset correspondant requis',cat_title:'Catalogues d’hébergeurs (expérimental)',cat_hint:'Sources JSON de catalogue, une URL par ligne. Volontairement non fournies — l’opérateur choisit les sources.',cat_urls:'URLs sources',cat_refresh:'Récupérer',cat_none:'aucune source — le chemin hébergeur est inactif',cat_items:'entrées au total',jd_hint:'Trois vues du même transfert : Romseerr voit les deux premières, JDownloader la troisième. Vide = défaut.',jd_watch:'Dossier surveillé (Romseerr écrit)',jd_out:'Dossier terminé (Romseerr lit)',jd_base:'Base de téléchargement (vue JDownloader)',var_prefs:'Versions (région/langue)',var_region_order:'Ordre des régions — l’ordre est la préférence',var_lang:'Langue préférée',var_prerelease:'Accepter bêta/prototype/démo',var_unspec:'non spécifié',var_preferred:'préféré',var_hint:'Repli pour toute l’instance. La région change le contenu (langue, difficulté, censure, 50/60 Hz) — ce n’est pas une échelle de qualité.',var_of:'Version',ra_achievements:'succès',ra_points:'points',ra_earned:'obtenus',ra_user:'Compte RetroAchievements (optionnel)',ra_refresh:'Récupérer les sets',ra_sets:'sets',ra_nokey:'aucune clé API',ra_unmapped:'sans correspondance de console',ra_only:'avec succès seulement',cov_of:'sur',cov_src:'Source',cov_asof:'au',cov_files:'fichiers',cov_missing:'titres manquants',cov_refresh:'Actualiser le catalogue',cov_nosnap:'pas d’instantané — catalogue pas encore récupéré',cov_nosource:'pas de source de catalogue pour cette plateforme',cov_basis:'Basé sur un instantané de {src} (max {max} titres par plateforme). Les jeux de métadonnées ne s’accordent pas sur ce qui compte comme titre distinct — le pourcentage est une orientation, pas une mesure.',cov_search:'Chercher',cov_none:'Rien ne manque (ou pas de catalogue).',cov_filter:'Filtrer …',cov_filter_do:'Filtrer',cov_wish_sel:'Sélection vers la liste',wl_import:'Import',wl_imp_hint:'Collez une liste ou choisissez un fichier (TXT/CSV) — un titre par ligne, éventuellement titre;plateforme. Rien n’est écrit avant votre confirmation.',wl_imp_example:'Télécharger un exemple',wl_imp_ph:'Chrono Trigger\nSuper Metroid;snes',wl_imp_preview:'Aperçu',wl_imp_apply:'Importer',wl_imp_none:'Rien de sélectionné.',wl_imp_done:'{a} importés, {s} ignorés.',wl_imp_trunc:'Seules les {n} premières lignes sont vérifiées.',wl_imp_toobig:'Fichier trop grand (max 200 ko).',wl_imp_nocheck:'Sans accès IGDB, pas de vérification — les entrées sont importées telles quelles.',wl_s_matched:'trouvé',wl_s_ambiguous:'ambigu',wl_s_notfound:'introuvable',wl_s_duplicate:'déjà suivi',wl_s_inlib:'déjà présent',wl_s_unverified:'non vérifié',add_wishlist:'⭐ Suivre',wl_added:'⭐ suivi',wl_empty:'Liste vide.',wl_remove:'Retirer',
 users:'Utilisateurs',new_user:'Créer un utilisateur',create:'Créer',del:'Supprimer',autoapprove:'Approbation auto',role_user:'Utilisateur',role_admin:'Admin',username:"Nom d'utilisateur",password:'Mot de passe',
 notif_discord:'Notifications — Discord',active:'activé',test:'Test',save:'Enregistrer',saved:'enregistré ✓',test_sent:'test envoyé ✓',webhook_ph:'URL du webhook Discord',
 st_pending:"⏳ En attente d'approbation",st_queued:'Demandé',st_downloading:'Téléchargement…',st_importing:'Traitement',st_done:'✅ Disponible',st_error:'Erreur',st_denied:'Refusé',st_exists:'présent',
 settings:'Paramètres',sec_general:'Général',sec_notif:'Notifications',sec_users:'Utilisateurs',sec_services:'Services',sec_about:'À propos',app_name:"Nom de l'app",default_lang:'Langue par défaut',refresh:'Actualiser',version:'Version',about_build:'Build',upd_avail:'Mise à jour disponible :',upd_current:'à jour',about_txt:'Clone de Seerr pour ROMs, fait maison.',wiz_welcome:'Bienvenue sur Romseerr',wiz_welcome_txt:'Cet assistant vous connecte aux services du stack (SABnzbd, Prowlarr, IGDB, RomM) étape par étape. Vous pouvez tester ou passer chaque étape.',wiz_done:'Terminé !',wiz_done_txt:'La configuration de base est prête. Vous pouvez tout ajuster plus tard dans Paramètres → Connexions.',wiz_next:'Suivant',wiz_back:'Retour',wiz_skip:'Passer',wiz_finish:'Commencer',wiz_step:'Étape',wiz_reopen:'Rouvrir l’assistant',about_lib:'Bibliothèque',about_titles:'titres',about_platforms:'plateformes',about_jobs:'Demandes',about_active:'actives',about_links:'Liens',about_feat:'Fonctions',about_feat_txt:'Recherche Archive.org + Usenet, dédup, découverte, demandes avec approbation, utilisateurs & droits, quotas, notifications, problèmes, PWA, API.',about_stack:'Stack',about_stack_txt:'Orchestre Prowlarr, SABnzbd, JDownloader et RomM. Connexions configurables dans Paramètres.',about_license:'Licence : MIT',sec_maint:'Journaux & maintenance',exp_title:'Export / import',exp_hint:'Sauvegarde paramètres, utilisateurs & droits, demandes et listes de souhaits en JSON. Sans phrase secrète, les secrets (mots de passe, clés API, URLs de webhook) sont EXCLUS — avec, ils sont joints chiffrés. La même phrase est requise à l’import.',exp_pass:'Phrase secrète',exp_pass_ph:'vide = sans secrets',exp_do:'Exporter',exp_merge:'Fusionner',exp_replace:'Remplacer',imp_do:'Importer',exp_done_plain:'Exporté (sans secrets).',exp_done_enc:'Exporté (secrets chiffrés).',imp_nofile:'Aucun fichier choisi.',imp_badjson:'Le fichier n’est pas du JSON valide.',imp_conf_merge:'Fusionner cet import ? Les valeurs existantes sont écrasées.',imp_conf_replace:'REMPLACER ? Utilisateurs, demandes et listes seront entièrement remplacés.',imp_done:'Importé :',logs:'Journal',clear_cache:'Vider le cache',reindex:'Réindexer',clear_finished:'Effacer terminés',done_word:'Terminé',lbl_jobs:'Demandes',lbl_lib:'Bibliothèque',sec_conn:'Connexions',reveal:'Afficher en clair',tls_hint:'Fournir le certificat + la clé (PEM) — l’app démarre alors un écouteur HTTPS sur le port choisi (redémarrage requis).',tls_none:'aucun certificat',tls_expires:'valide jusqu’au',tls_key_note:'clé privée — jamais affichée',tls_restart:'redémarrer le conteneur pour activer',conn_hint:'Les champs vides utilisent la valeur de l’environnement (.env). Les secrets sont masqués — laisser vide conserve la valeur.',
 profile:'Profil',display_name:'Nom affiché',email:'E-mail',language:'Langue',design:'Thème',default_design:'Thème par défaut',d_seerr:'Seerr',d_glass:'Verre',d_clean:'Épuré',avatar:'Avatar',pwebhook:'Webhook Discord personnel',change_pw:'Changer le mot de passe',cur_pw:'Mot de passe actuel',new_pw:'Nouveau mot de passe',choose_img:'Choisir une image',saved_ok:'enregistré ✓',
 blocklist:'Liste de blocage',add_btn:'Ajouter',pattern_ph:'Mot-clé/motif dans le titre',
 nav_issues:'🐞 Problèmes',nav_messages:'Messages',msg_to:'À',msg_none:'Aucun message.',msg_ph:'Écrire un message …',msg_send:'Envoyer',msg_hint:'Ctrl+Entrée envoie',msg_nousers:'Aucun autre utilisateur.',req_for:'Demande pour',req_self:'moi-même',issues:'Problèmes',report_issue:'Signaler un problème',issue_msg:'Message',close_btn:'Fermer',st_open:'ouvert',st_closed:'fermé',submit:'Envoyer',issue_type:'Type',comment_ph:'Écrire un commentaire …',comment_send:'Envoyer',push_enable:'🔔 Activer push',push_disable:'🔕 Désactiver push',push_unsupported:'Push indisponible (HTTPS requis)',push_denied:'Permission refusée',push_on:'Push activé ✓',push_off:'Push désactivé'
},es:{
 nav_discover:'🔍 Descubrir',nav_requests:'📥 Solicitudes',nav_users:'👤 Usuarios',nav_settings:'⚙️ Ajustes',logout:'🚪 Salir',
 search_ph:'Buscar un juego … (Intro)',platforms:'Plataformas',all:'Todas',selected:'seleccionado',
 hint_type:'Escribe un título y pulsa Intro.',loading_home:'Cargando …',popular_on:'Popular en',click_search:'clic para buscar',
 searching:'Buscando …',no_results:'Sin resultados.',results:'resultados',in_library:'✓ en la biblioteca',download:'⬇ Descargar',requested:'✓ solicitado',collection:'Colección',
 versions:'Versiones / fuentes',files:'Archivos',no_desc:'Sin descripción disponible.',screenshots:'Capturas',similar:'Juegos similares',series:'Serie',because_you:'Porque solicitaste:',
 no_requests:'Aún no hay solicitudes.',approve:'Aprobar',deny:'Rechazar',retry:'Reintentar',reset:'Restablecer todo',req_all:'Solicitar todo',flt_user:'Usuario',flt_all:'Todos',wishlist:'Lista de deseos',nav_coverage:'Cobertura',emu_rb_confirm:'¿Volver {n} a la versión anterior?',emu_rb_failed:'reversión fallida',emu_update:'Actualizar emuladores',emu_nohost:'sin host de transmisión',emu_nolauncher:'sin servicio de lanzamiento',emu_unreachable:'servicio inalcanzable',emu_running:'actualización en curso …',emu_none:'sin emuladores instalados',emu_ok:'última vez correcto',emu_failed:'última vez fallido',stream:'Transmitir',stream_single:'plaza única — una sesión a la vez',stream_busy:'Ocupado: {u} está jugando {g}',stream_stop:'Terminar sesión',stream_not_in_lib:'El título debe estar en la biblioteca.',stream_no:'Transmisión no disponible.',stream_running:'▶ en marcha — ventana abierta',stream_manual:'escritorio abierto — inicia el título allí',stream_title:'Host de transmisión',stream_hint:'Para plataformas que el navegador no puede emular (PS2, GameCube, Wii, Switch).',stream_url_l:'URL del host en el navegador',stream_launch_l:'Servicio de lanzamiento (opcional)',sec_outbound:'Peticiones salientes',outbound_hint:'Las URLs de webhook las ponen los usuarios. Por defecto se rechazan destinos privados, loopback y link-local. Permítelos explícitamente si tu destino está en la misma red.',outbound_allow:'Permitir destinos en red privada',play:'Jugar en el navegador',play_no_romm:'No es posible — RomM no está conectado.',play_no_core:'Esta plataforma no se puede emular en el navegador.',play_not_in_lib:'El título debe estar en la biblioteca.',play_too_large:'Demasiado grande para el navegador (límite {mb} MB).',play_no_title:'Sin título.',play_bios:'necesita BIOS',play_romset:'arcade: solo con el romset adecuado',cat_title:'Catálogos de hosters (experimental)',cat_hint:'Fuentes JSON de catálogo, una URL por línea. Deliberadamente no incluidas — el operador elige las fuentes.',cat_urls:'URLs de origen',cat_refresh:'Obtener ahora',cat_none:'sin fuente — la vía de hoster está inactiva',cat_items:'entradas en total',jd_hint:'Tres vistas de la misma entrega: Romseerr ve las dos primeras, JDownloader la tercera. Vacío = predeterminado.',jd_watch:'Carpeta vigilada (escribe Romseerr)',jd_out:'Carpeta terminada (lee Romseerr)',jd_base:'Base de descarga (vista de JDownloader)',var_prefs:'Versiones (región/idioma)',var_region_order:'Orden de regiones — el orden es la preferencia',var_lang:'Idioma preferido',var_prerelease:'Aceptar beta/prototipo/demo',var_unspec:'sin especificar',var_preferred:'preferida',var_hint:'Valor de reserva para toda la instancia. La región cambia el contenido (idioma, dificultad, censura, 50/60 Hz) — no es una escala de calidad.',var_of:'Versión',ra_achievements:'logros',ra_points:'puntos',ra_earned:'obtenidos',ra_user:'Cuenta RetroAchievements (opcional)',ra_refresh:'Obtener sets',ra_sets:'sets',ra_nokey:'sin clave API',ra_unmapped:'sin correspondencia de consola',ra_only:'solo con logros',cov_of:'de',cov_src:'Fuente',cov_asof:'a fecha',cov_files:'archivos',cov_missing:'títulos que faltan',cov_refresh:'Actualizar catálogo',cov_nosnap:'sin instantánea — catálogo aún no obtenido',cov_nosource:'sin fuente de catálogo para esta plataforma',cov_basis:'Basado en una instantánea de {src} (máx. {max} títulos por plataforma). Los conjuntos de metadatos no coinciden en qué cuenta como título propio — el porcentaje orienta, no mide.',cov_search:'Buscar',cov_none:'No falta nada (o no hay catálogo).',cov_filter:'Filtrar …',cov_filter_do:'Filtrar',cov_wish_sel:'Selección a la lista',wl_import:'Importar',wl_imp_hint:'Pega una lista o elige un archivo (TXT/CSV) — un título por línea, opcionalmente título;plataforma. No se escribe nada hasta que confirmes.',wl_imp_example:'Descargar archivo de ejemplo',wl_imp_ph:'Chrono Trigger\nSuper Metroid;snes',wl_imp_preview:'Vista previa',wl_imp_apply:'Importar',wl_imp_none:'Nada seleccionado.',wl_imp_done:'{a} importados, {s} omitidos.',wl_imp_trunc:'Solo se comprueban las primeras {n} líneas.',wl_imp_toobig:'Archivo demasiado grande (máx. 200 kB).',wl_imp_nocheck:'Sin acceso a IGDB no hay comprobación — se importan sin verificar.',wl_s_matched:'encontrado',wl_s_ambiguous:'ambiguo',wl_s_notfound:'no encontrado',wl_s_duplicate:'ya en la lista',wl_s_inlib:'ya en biblioteca',wl_s_unverified:'sin verificar',add_wishlist:'⭐ Seguir',wl_added:'⭐ en lista',wl_empty:'Lista vacía.',wl_remove:'Quitar',
 users:'Usuarios',new_user:'Crear usuario',create:'Crear',del:'Eliminar',autoapprove:'Auto-aprobación',role_user:'Usuario',role_admin:'Admin',username:'Usuario',password:'Contraseña',
 notif_discord:'Notificaciones — Discord',active:'activo',test:'Prueba',save:'Guardar',saved:'guardado ✓',test_sent:'prueba enviada ✓',webhook_ph:'URL del webhook de Discord',
 st_pending:'⏳ Esperando aprobación',st_queued:'Solicitado',st_downloading:'Descargando…',st_importing:'Procesando',st_done:'✅ Disponible',st_error:'Error',st_denied:'Rechazado',st_exists:'presente',
 settings:'Ajustes',sec_general:'General',sec_notif:'Notificaciones',sec_users:'Usuarios',sec_services:'Servicios',sec_about:'Acerca de',app_name:'Nombre de la app',default_lang:'Idioma predeterminado',refresh:'Actualizar',version:'Versión',about_build:'Build',upd_avail:'Actualización disponible:',upd_current:'actualizado',about_txt:'Clon de Seerr para ROMs, hecho en casa.',wiz_welcome:'Bienvenido a Romseerr',wiz_welcome_txt:'Este asistente te conecta con los servicios del stack (SABnzbd, Prowlarr, IGDB, RomM) paso a paso. Puedes probar u omitir cada paso.',wiz_done:'¡Listo!',wiz_done_txt:'La configuración básica está hecha. Puedes ajustar todo luego en Ajustes → Conexiones.',wiz_next:'Siguiente',wiz_back:'Atrás',wiz_skip:'Omitir',wiz_finish:'Empezar',wiz_step:'Paso',wiz_reopen:'Reabrir asistente',about_lib:'Biblioteca',about_titles:'títulos',about_platforms:'plataformas',about_jobs:'Solicitudes',about_active:'activas',about_links:'Enlaces',about_feat:'Funciones',about_feat_txt:'Búsqueda en Archive.org + Usenet, dedup, descubrir, solicitudes con aprobación, usuarios y permisos, cuotas, notificaciones, problemas, PWA, API.',about_stack:'Stack',about_stack_txt:'Orquesta Prowlarr, SABnzbd, JDownloader y RomM. Conexiones configurables en Ajustes.',about_license:'Licencia: MIT',sec_maint:'Registros y mantenimiento',exp_title:'Exportar / importar',exp_hint:'Guarda ajustes, usuarios y permisos, solicitudes y listas de deseos como JSON. Sin frase de contraseña los secretos (contraseñas, claves API, URLs de webhook) QUEDAN FUERA — con ella se adjuntan cifrados. La misma frase hace falta al importar.',exp_pass:'Frase de contraseña',exp_pass_ph:'vacío = sin secretos',exp_do:'Exportar',exp_merge:'Combinar',exp_replace:'Reemplazar',imp_do:'Importar',exp_done_plain:'Exportado (sin secretos).',exp_done_enc:'Exportado (secretos cifrados).',imp_nofile:'Ningún archivo seleccionado.',imp_badjson:'El archivo no es JSON válido.',imp_conf_merge:'¿Combinar esta importación? Los valores existentes se sobrescriben.',imp_conf_replace:'¿REEMPLAZAR? Usuarios, solicitudes y listas se sustituyen por completo.',imp_done:'Importado:',logs:'Registro',clear_cache:'Vaciar caché',reindex:'Reindexar',clear_finished:'Borrar terminados',done_word:'Hecho',lbl_jobs:'Solicitudes',lbl_lib:'Biblioteca',sec_conn:'Conexiones',reveal:'Mostrar en texto plano',tls_hint:'Proporciona certificado + clave (PEM) — la app inicia además un listener HTTPS en el puerto elegido (requiere reinicio).',tls_none:'sin certificado',tls_expires:'válido hasta',tls_key_note:'clave privada — nunca se muestra',tls_restart:'reinicia el contenedor para activar',conn_hint:'Los campos vacíos usan el valor del entorno (.env). Los secretos se enmascaran — dejar vacío conserva el valor.',
 profile:'Perfil',display_name:'Nombre visible',email:'Correo',language:'Idioma',design:'Diseño',default_design:'Diseño predeterminado',d_seerr:'Seerr',d_glass:'Cristal',d_clean:'Limpio',avatar:'Avatar',pwebhook:'Webhook de Discord personal',change_pw:'Cambiar contraseña',cur_pw:'Contraseña actual',new_pw:'Nueva contraseña',choose_img:'Elegir imagen',saved_ok:'guardado ✓',
 blocklist:'Lista de bloqueo',add_btn:'Añadir',pattern_ph:'Palabra clave/patrón en el título',
 nav_issues:'🐞 Problemas',nav_messages:'Mensajes',msg_to:'Para',msg_none:'Sin mensajes.',msg_ph:'Escribe un mensaje …',msg_send:'Enviar',msg_hint:'Ctrl+Enter envía',msg_nousers:'No hay otros usuarios.',req_for:'Solicitud para',req_self:'yo mismo',issues:'Problemas',report_issue:'Informar problema',issue_msg:'Mensaje',close_btn:'Cerrar',st_open:'abierto',st_closed:'cerrado',submit:'Enviar',issue_type:'Tipo',comment_ph:'Escribe un comentario …',comment_send:'Enviar',push_enable:'🔔 Activar push',push_disable:'🔕 Desactivar push',push_unsupported:'Push no disponible (requiere HTTPS)',push_denied:'Permiso denegado',push_on:'Push activado ✓',push_off:'Push desactivado'
},it:{
 nav_discover:'🔍 Scopri',nav_requests:'📥 Richieste',nav_users:'👤 Utenti',nav_settings:'⚙️ Impostazioni',logout:'🚪 Esci',
 search_ph:'Cerca un gioco … (Invio)',platforms:'Piattaforme',all:'Tutte',selected:'selezionate',
 hint_type:'Digita un titolo e premi Invio.',loading_home:'Caricamento …',popular_on:'Popolari su',click_search:'clicca per cercare',
 searching:'Ricerca …',no_results:'Nessun risultato.',results:'risultati',in_library:'✓ in libreria',download:'⬇ Scarica',requested:'✓ richiesto',collection:'Collezione',
 versions:'Versioni / fonti',files:'File',no_desc:'Nessuna descrizione disponibile.',screenshots:'Screenshot',similar:'Giochi simili',series:'Serie',because_you:'Perché hai richiesto:',
 no_requests:'Ancora nessuna richiesta.',approve:'Approva',deny:'Rifiuta',retry:'Riprova',reset:'Reimposta tutto',req_all:'Richiedi tutto',flt_user:'Utente',flt_all:'Tutti',wishlist:'Lista dei desideri',nav_coverage:'Copertura',emu_rb_confirm:'Ripristinare {n} alla versione precedente?',emu_rb_failed:'ripristino fallito',emu_update:'Aggiorna emulatori',emu_nohost:'nessun host di streaming',emu_nolauncher:'nessun servizio di avvio',emu_unreachable:'servizio irraggiungibile',emu_running:'aggiornamento in corso …',emu_none:'nessun emulatore installato',emu_ok:'ultima esecuzione riuscita',emu_failed:'ultima esecuzione fallita',stream:'Trasmetti',stream_single:'posto singolo — una sessione alla volta',stream_busy:'Occupato: {u} sta giocando a {g}',stream_stop:'Termina sessione',stream_not_in_lib:'Il titolo deve essere in libreria.',stream_no:'Streaming non disponibile.',stream_running:'▶ in esecuzione — finestra aperta',stream_manual:'desktop aperto — avvia lì il titolo',stream_title:'Host di streaming',stream_hint:'Per piattaforme che il browser non può emulare (PS2, GameCube, Wii, Switch).',stream_url_l:'URL del host nel browser',stream_launch_l:'Servizio di avvio (opzionale)',sec_outbound:'Richieste in uscita',outbound_hint:'Gli URL dei webhook li imposta l’utente. Per impostazione predefinita i destinatari privati, loopback e link-local vengono rifiutati. Consentili esplicitamente se il tuo destinatario è nella stessa rete.',outbound_allow:'Consenti destinatari in rete privata',play:'Gioca nel browser',play_no_romm:'Non possibile — RomM non è connesso.',play_no_core:'Questa piattaforma non è emulabile nel browser.',play_not_in_lib:'Il titolo deve essere in libreria.',play_too_large:'Troppo grande per il browser (limite {mb} MB).',play_no_title:'Nessun titolo.',play_bios:'richiede il BIOS',play_romset:'arcade: solo con il romset corretto',cat_title:'Cataloghi filehoster (sperimentale)',cat_hint:'Fonti JSON di catalogo, una URL per riga. Volutamente non incluse — le fonti le sceglie l’operatore.',cat_urls:'URL delle fonti',cat_refresh:'Recupera ora',cat_none:'nessuna fonte — il percorso filehoster è inattivo',cat_items:'voci in totale',jd_hint:'Tre viste sullo stesso passaggio: Romseerr vede le prime due, JDownloader la terza. Vuoto = predefinito.',jd_watch:'Cartella osservata (scrive Romseerr)',jd_out:'Cartella completata (legge Romseerr)',jd_base:'Base di download (vista JDownloader)',var_prefs:'Versioni (regione/lingua)',var_region_order:'Ordine delle regioni — l’ordine è la preferenza',var_lang:'Lingua preferita',var_prerelease:'Accetta beta/prototipo/demo',var_unspec:'non specificato',var_preferred:'preferita',var_hint:'Ripiego per tutta l’istanza. La regione cambia il contenuto (lingua, difficoltà, censura, 50/60 Hz) — non è una scala di qualità.',var_of:'Versione',ra_achievements:'obiettivi',ra_points:'punti',ra_earned:'ottenuti',ra_user:'Account RetroAchievements (opzionale)',ra_refresh:'Recupera i set',ra_sets:'set',ra_nokey:'nessuna chiave API',ra_unmapped:'senza mappatura console',ra_only:'solo con obiettivi',cov_of:'di',cov_src:'Fonte',cov_asof:'al',cov_files:'file',cov_missing:'titoli mancanti',cov_refresh:'Aggiorna catalogo',cov_nosnap:'nessuna istantanea — catalogo non ancora recuperato',cov_nosource:'nessuna fonte di catalogo per questa piattaforma',cov_basis:'Basato su un’istantanea da {src} (max {max} titoli per piattaforma). I set di metadati non concordano su cosa sia un titolo distinto — la percentuale orienta, non misura.',cov_search:'Cerca',cov_none:'Non manca nulla (o nessun catalogo).',cov_filter:'Filtra …',cov_filter_do:'Filtra',cov_wish_sel:'Selezione alla lista',wl_import:'Importa',wl_imp_hint:'Incolla un elenco o scegli un file (TXT/CSV) — un titolo per riga, opzionalmente titolo;piattaforma. Nulla viene scritto prima della conferma.',wl_imp_example:'Scarica file di esempio',wl_imp_ph:'Chrono Trigger\nSuper Metroid;snes',wl_imp_preview:'Anteprima',wl_imp_apply:'Importa',wl_imp_none:'Niente selezionato.',wl_imp_done:'{a} importati, {s} saltati.',wl_imp_trunc:'Vengono controllate solo le prime {n} righe.',wl_imp_toobig:'File troppo grande (max 200 kB).',wl_imp_nocheck:'Senza accesso IGDB nessun controllo — le voci vengono importate non verificate.',wl_s_matched:'trovato',wl_s_ambiguous:'ambiguo',wl_s_notfound:'non trovato',wl_s_duplicate:'già in lista',wl_s_inlib:'già in libreria',wl_s_unverified:'non verificato',add_wishlist:'⭐ Segui',wl_added:'⭐ seguito',wl_empty:'Lista vuota.',wl_remove:'Rimuovi',
 users:'Utenti',new_user:'Crea utente',create:'Crea',del:'Elimina',autoapprove:'Auto-approvazione',role_user:'Utente',role_admin:'Admin',username:'Utente',password:'Password',
 notif_discord:'Notifiche — Discord',active:'attivo',test:'Test',save:'Salva',saved:'salvato ✓',test_sent:'test inviato ✓',webhook_ph:'URL webhook Discord',
 st_pending:'⏳ In attesa di approvazione',st_queued:'Richiesto',st_downloading:'Scaricamento…',st_importing:'Elaborazione',st_done:'✅ Disponibile',st_error:'Errore',st_denied:'Rifiutato',st_exists:'presente',
 settings:'Impostazioni',sec_general:'Generale',sec_notif:'Notifiche',sec_users:'Utenti',sec_services:'Servizi',sec_about:'Informazioni',app_name:'Nome dell’app',default_lang:'Lingua predefinita',refresh:'Aggiorna',version:'Versione',about_build:'Build',upd_avail:'Aggiornamento disponibile:',upd_current:'aggiornato',about_txt:'Clone di Seerr per ROM, fatto in casa.',wiz_welcome:'Benvenuto in Romseerr',wiz_welcome_txt:'Questa procedura ti collega ai servizi dello stack (SABnzbd, Prowlarr, IGDB, RomM) passo dopo passo. Puoi testare o saltare ogni passaggio.',wiz_done:'Fatto!',wiz_done_txt:'La configurazione di base è pronta. Puoi regolare tutto in seguito in Impostazioni → Connessioni.',wiz_next:'Avanti',wiz_back:'Indietro',wiz_skip:'Salta',wiz_finish:'Inizia',wiz_step:'Passo',wiz_reopen:'Riapri procedura',about_lib:'Libreria',about_titles:'titoli',about_platforms:'piattaforme',about_jobs:'Richieste',about_active:'attive',about_links:'Link',about_feat:'Funzioni',about_feat_txt:'Ricerca su Archive.org + Usenet, dedup, scoperta, richieste con approvazione, utenti e permessi, quote, notifiche, problemi, PWA, API.',about_stack:'Stack',about_stack_txt:'Orchestra Prowlarr, SABnzbd, JDownloader e RomM. Connessioni configurabili nelle Impostazioni.',about_license:'Licenza: MIT',sec_maint:'Log e manutenzione',exp_title:'Esporta / importa',exp_hint:'Salva impostazioni, utenti e permessi, richieste e liste dei desideri come JSON. Senza passphrase i segreti (password, chiavi API, URL webhook) restano ESCLUSI — con la passphrase vengono allegati cifrati. La stessa passphrase serve all’importazione.',exp_pass:'Passphrase',exp_pass_ph:'vuoto = senza segreti',exp_do:'Esporta',exp_merge:'Unisci',exp_replace:'Sostituisci',imp_do:'Importa',exp_done_plain:'Esportato (senza segreti).',exp_done_enc:'Esportato (segreti cifrati).',imp_nofile:'Nessun file scelto.',imp_badjson:'Il file non è JSON valido.',imp_conf_merge:'Unire questa importazione? I valori esistenti vengono sovrascritti.',imp_conf_replace:'SOSTITUIRE? Utenti, richieste e liste vengono sostituiti del tutto.',imp_done:'Importato:',logs:'Log',clear_cache:'Svuota cache',reindex:'Reindicizza',clear_finished:'Cancella completati',done_word:'Fatto',lbl_jobs:'Richieste',lbl_lib:'Libreria',sec_conn:'Connessioni',reveal:'Mostra in chiaro',tls_hint:'Fornisci certificato + chiave (PEM) — l’app avvia anche un listener HTTPS sulla porta scelta (riavvio necessario).',tls_none:'nessun certificato',tls_expires:'valido fino al',tls_key_note:'chiave privata — mai mostrata',tls_restart:'riavvia il container per attivare',conn_hint:'I campi vuoti usano il valore dell’ambiente (.env). I segreti sono mascherati — lasciare vuoto mantiene il valore.',
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
function setLang(l){LANG=l;localStorage.setItem('lang',l);applyI18n();
 document.querySelectorAll('#langsw b').forEach(e=>e.classList.toggle('on',e.dataset.l==l));
 if(cur=='s'&&!document.getElementById('q').value.trim())loadDiscover();if(cur=='j')loadJobs();}
function applyI18n(){
 document.querySelectorAll('[data-i18n]').forEach(e=>e.textContent=t(e.dataset.i18n));
 document.querySelectorAll('[data-i18n-ph]').forEach(e=>e.placeholder=t(e.dataset.i18nPh));
 updateFLabel();}
let cur='s';
function show(v){cur=v;
 document.getElementById('discview').style.display=v=='s'?'':'none';
 document.getElementById('jobs').style.display=v=='j'?'block':'none';
 document.getElementById('settings').style.display=v=='set'?'block':'none';
 document.getElementById('issues').style.display=v=='issues'?'block':'none';
 document.getElementById('messages').style.display=v=='msg'?'block':'none';
 document.getElementById('coverage').style.display=v=='cov'?'block':'none';
 document.getElementById('nS').classList.toggle('on',v=='s');
 document.getElementById('nJ').classList.toggle('on',v=='j');
 document.getElementById('nI').classList.toggle('on',v=='issues');
 let nM=document.getElementById('nM');if(nM)nM.classList.toggle('on',v=='msg');
 document.getElementById('nSet').classList.toggle('on',v=='set');
 if(v=='j')loadJobs();if(v=='set')openSettingsView();
 if(v=='issues'){loadIssues(window._ipref);window._ipref=null;}
 let nC=document.getElementById('nC');if(nC)nC.classList.toggle('on',v=='cov');
 if(v=='msg')loadMessages();if(v=='cov')loadCoverage();}
// --- Abdeckung je Plattform: „was fehlt mir" statt „was habe ich" (#78) ---
// Jede Zahl traegt Quelle + Stand — eine nackte Prozentzahl waere hier irrefuehrend.
async function loadCoverage(){let box=document.getElementById('coverage');
 box.innerHTML='<div class=meta>…</div>';
 let d=await(await fetch('/api/coverage')).json();
 let rows=(d.platforms||[]).map(p=>{
  if(p.known==null)return `<div class=job><div><b>${p.name}</b><div class=meta style="font-size:11px">`
    +(p.catalog?t('cov_nosnap'):t('cov_nosource'))+` · ${p.files} ${t('cov_files')}</div></div></div>`;
  let bar=`<div style="background:#2a2f37;border-radius:4px;height:6px;width:120px;overflow:hidden">`
   +`<div style="background:#6c5ce7;height:6px;width:${Math.min(100,p.pct||0)}%"></div></div>`;
  return `<div class=job style="cursor:pointer" onclick="openMissing('${p.slug}','${p.name.replace(/'/g,"")}')">
   <div><b>${p.name}</b><div class=meta style="font-size:11px">${p.owned} ${t('cov_of')} ${p.known}`
   +(p.capped?' +':'')+` · ${p.pct}% · ${t('cov_src')}: ${p.source} · ${t('cov_asof')} ${(p.snapshot||'').slice(0,10)}</div></div>
   <div style="display:flex;align-items:center;gap:10px">${bar}<span class=meta>›</span></div></div>`;}).join('');
 let adm=canDo('manage_settings')?`<button onclick="covRefresh()">${t('cov_refresh')}</button>
   <span id=covmsg class=meta></span>`:'';
 box.innerHTML=`<div class=rowh style="display:flex;align-items:center;gap:10px"><b>📊 ${t('nav_coverage')}</b>
   <span style="margin-left:auto">${adm}</span></div>
  <div class=meta style="margin:6px 0 10px;line-height:1.6">${t('cov_basis').replace('{src}',d.source).replace('{max}',d.max_per_platform)}</div>
  ${rows}`;
 if(d.building)covPoll();}
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
function renderCard(it){let c=document.createElement('div');c.className='card';
 let cov=it.cover?`background-image:url('${it.cover}')`:'';
 let src=it.source=='usenet'?'📡 Usenet':'🗄 Archive';
 let settag=it.is_set?' · 📦 '+t('collection'):'';
 c.innerHTML=`<div class=cover style="${cov}"><span class=badge>${it.platform_slug||'?'}</span><span class=src>${src}</span></div>
  <div class=body><div class=t>${it.title.replace(/</g,'&lt;')}</div><div class=meta>${sz(it.size)}${settag}</div><div class=act></div></div>`;
 c.querySelector('.cover').onclick=()=>openDetail(it);
 let tt=c.querySelector('.t');tt.style.cursor='pointer';tt.onclick=()=>openDetail(it);
 let act=c.querySelector('.act');
 if(it.in_library)act.innerHTML='<div class=have>'+t('in_library')+'</div>';
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
async function openDetail(it){let m=document.getElementById('modal');m.style.display='block';window._detit=it;window.reqFor='';
 let vars=(window.LASTRES||[]).filter(x=>x.gkey&&x.gkey===it.gkey);
 m.innerHTML=`<div class=box><button class=x onclick="closeModal()">×</button>
  <div class=top><div class=mc style="${it.cover?`background-image:url('${it.cover}')`:''}"></div>
   <div><h2>${it.title.replace(/</g,'&lt;')}</h2>
    <div class=meta>${it.platform_slug||'?'} · ${it.source=='usenet'?'📡 Usenet':'🗄 Archive'} · ${sz(it.size)}${it.is_set?' · 📦 Sammlung':''}</div>
    <div class=meta2 id=mrich></div>
    <button onclick="reportFromDetail()" style="margin-top:8px;background:#2a2f37;border:none;color:#fff;padding:6px 10px;border-radius:6px;cursor:pointer;font-size:12px">🐞 ${t('report_issue')}</button>
    <button id=wlbtn onclick="addWishlist(this)" style="margin-top:8px;margin-left:6px;background:#2a2f37;border:none;color:#fff;padding:6px 10px;border-radius:6px;cursor:pointer;font-size:12px">${t('add_wishlist')}</button>
    <div class=desc id=mdesc>…</div></div></div>
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
 if(canDo('manage_requests')){try{let us=await(await fetch('/api/users')).json();let names=Object.keys(us||{});
   if(names.length){let bar=document.getElementById('reqforbar');
    bar.innerHTML=`<div class=frow style="margin-bottom:8px"><label style="min-width:auto;color:#8b929e;font-size:12px">${t('req_for')}</label><select id=reqforsel onchange="window.reqFor=this.value"><option value="">${t('req_self')}</option>${names.map(u=>`<option value="${u}">${u.replace(/</g,'&lt;')}</option>`).join('')}</select></div>`;}}catch(e){}}
 let r=await fetch('/api/detail?source='+encodeURIComponent(it.source)+'&ref='+encodeURIComponent(it.ref||'')+'&title='+encodeURIComponent(it.title)+'&platform='+encodeURIComponent(it.platform_slug||''));
 let d=await r.json();
 window._detname=d.name||'';
 // RetroAchievements: nur wenn ein Set zugeordnet ist. Kein Set / kein Dienst -> gar nichts. (#79)
 loadPlay(it);loadStream(it);
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
 s.textContent=`${v.source=='usenet'?'📡':'🗄'} ${sz(v.size)} · ${v.platform_slug} · ${v.title.slice(0,48)}`;
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
 btn.textContent=d.launched?t('stream_running'):t('stream_manual');
 window.open(d.url,'_blank','noopener');}
async function stopStream(){await fetch('/api/stream/stop',{method:'POST'});closeModal();}
function closeModal(){document.getElementById('modal').style.display='none';}
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
   c.innerHTML=`<div class=pcover style="${it.cover?`background-image:url('${it.cover}')`:''}">${it.in_library?'<span class=have2>✓</span>':''}</div><div class=pt>${it.title.replace(/</g,'&lt;')}</div>`;
   c.onclick=()=>{SELP=r.slug?new Set([r.slug]):new Set();
    localStorage.setItem('romp',JSON.stringify([...SELP]));updateFLabel();
    document.querySelectorAll('.chip').forEach(e=>e.classList.toggle('on',SELP.has(e.dataset.s)));
    document.getElementById('q').value=it.title;search();};
   strip.appendChild(c);});
  g.appendChild(sec);});}
function toggleDiscCust(){let e=document.getElementById('disccust');e.style.display=e.style.display=='none'?'block':'none';}
const STCLS={downloading:'downloading',importing:'importing',done:'done',error:'error',denied:'error'};
function stlab(s){return [t('st_'+s)||s, STCLS[s]||''];}
async function loadJobs(){let r=await fetch('/api/jobs');let d=await r.json();let j=document.getElementById('jobs');
 j.innerHTML='';
 try{let wl=await(await fetch('/api/wishlist')).json();
  let box=document.createElement('div');box.style.cssText='margin-bottom:14px';
  box.innerHTML='<div class=rowh style="margin-bottom:6px;display:flex;align-items:center;gap:8px">⭐ <b>'+t('wishlist')+'</b>'
   +'<button onclick="openWlImport()" style="margin-left:auto;background:#2a2f37;border:none;color:#e6e8ec;padding:5px 10px;border-radius:6px;cursor:pointer;font-size:12px">'+t('wl_import')+'</button></div>';
  if(wl&&wl.length){
   wl.forEach(e=>{let row=document.createElement('div');row.className='job';
    row.innerHTML=`<div><div>${(e.title||'').replace(/</g,'&lt;')}</div><div class=meta style="color:#8b929e;font-size:11px">${(e.platform||'—').replace(/</g,'&lt;')}</div></div>`;
    let b=document.createElement('button');b.textContent=t('wl_remove');
    b.style.cssText='background:#6e2a2a;border:none;color:#fff;padding:5px 10px;border-radius:6px;cursor:pointer';
    b.onclick=async()=>{await fetch('/api/wishlist/remove',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:e.title,platform:e.platform})});loadJobs();};
    row.appendChild(b);box.appendChild(row);});
  }else{let em=document.createElement('div');em.className='meta';em.textContent=t('wl_empty');box.appendChild(em);}
  j.appendChild(box);}catch(e){}
 if(canDo('manage_requests')){let users=[...new Set(d.map(o=>o.user||'—'))].sort();
  if(users.length>1){let bar=document.createElement('div');bar.style.cssText='margin:0 0 10px;color:#8b929e;font-size:13px';
   let opts='<option value="">'+t('flt_all')+'</option>'+users.map(u=>`<option${window.jobFilter===u?' selected':''}>${u.replace(/</g,'&lt;')}</option>`).join('');
   bar.innerHTML=t('flt_user')+': <select id=jobflt onchange="window.jobFilter=this.value;loadJobs()" style="background:#1a1d23;color:#e6e8ec;border:1px solid #2a2f37;border-radius:6px;padding:4px 8px">'+opts+'</select>';
   j.appendChild(bar);}}
 if(window.jobFilter)d=d.filter(o=>(o.user||'—')===window.jobFilter);
 if(!d.length){let h=document.createElement('div');h.className='hint';h.textContent=t('no_requests');j.appendChild(h);return;}
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
async function loadPlatforms(){
 let r=await fetch('/api/platforms');let d=await r.json();
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
 window.ROLE=d.role;window.VERSION=d.version||'';window.PERMS=d.perms||[];
 let lang=d.user_lang||localStorage.getItem('lang')||d.default_lang||'de';
 if(lang!=LANG){LANG=lang;localStorage.setItem('lang',lang);setLang(lang);}
 applyDesign(d.user_design||localStorage.getItem('design')||d.default_design||'seerr');
 let who=document.getElementById('who');
 if(d.user){let nm=(d.display_name||d.user);
   who.innerHTML=`<img src="${d.avatar||defAvatar(nm)}">`+nm.replace(/</g,'&lt;');}
 else who.textContent='';
 if(d.role=='admin'){document.getElementById('nSet').style.display='';
   try{let cs=await(await fetch('/api/settings')).json();if(!cs.onboarded)startWizard();}catch(e){}}}
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
let SETSEC='general';
function openSettingsView(){
 let secs=[['general',t('sec_general')],['notif',t('sec_notif')],['conn',t('sec_conn')],['users',t('sec_users')],['blocklist',t('blocklist')],['services',t('sec_services')],['maint',t('sec_maint')],['tls','HTTPS'],['about',t('sec_about')]];
 document.getElementById('settings').innerHTML='<div class=setwrap><div class=setnav>'+
  secs.map(x=>`<a class=snav data-sec="${x[0]}" onclick="setSection('${x[0]}')">${x[1]}</a>`).join('')+
  '</div><div id=setcontent></div></div>';
 setSection(SETSEC);}
function setSection(sec){SETSEC=sec;
 document.querySelectorAll('.snav').forEach(e=>e.classList.toggle('on',e.dataset.sec==sec));
 let c=document.getElementById('setcontent');
 ({general:secGeneral,notif:secNotif,conn:secConn,users:secUsers,blocklist:secBlocklist,services:secServices,maint:secMaint,tls:secTls,about:secAbout}[sec]||secGeneral)(c);}
async function secConn(c){let vals=await(await fetch('/api/settings/connections/reveal')).json();
 function fld(k,label,secret){let v=(vals[k]||'');
  let eye=secret?`<button type=button onclick="togEye('c_${k}',this)" title="${t('reveal')}" style="background:#2a2f37;border:none;color:#8b929e;padding:6px 9px;border-radius:6px;cursor:pointer;margin-left:6px">👁</button>`:'';
  return `<div class=frow><label style="min-width:150px">${label}</label><input id="c_${k}" ${secret?'type=password':''} value="${(''+v).replace(/"/g,'&quot;')}" style="flex:1">${eye}</div>`;}
 c.innerHTML=`<h3>${t('sec_conn')}</h3><div class=meta style="margin-bottom:10px">${t('conn_hint')}</div>
  <h3 style="font-size:13px">SABnzbd</h3>${fld('sab_url','URL')}${fld('sab_apikey','API-Key',1)}${fld('sab_cat','Kategorie / category')}
  <h3 style="font-size:13px">Prowlarr</h3>${fld('prow_url','URL')}${fld('prow_apikey','API-Key',1)}${fld('prow_cats','Kategorien / categories')}
  <h3 style="font-size:13px">IGDB</h3>${fld('igdb_id','Client-ID')}${fld('igdb_secret','Client-Secret',1)}
  <h3 style="font-size:13px">Scraper / Cover-Quellen</h3>${fld('sgdb_key','SteamGridDB-Key',1)}${fld('ss_user','ScreenScraper-User')}${fld('ss_pass','ScreenScraper-Passwort',1)}
  <h3 style="font-size:13px">RomM</h3>${fld('romm_url','URL')}${fld('romm_user','User')}${fld('romm_pass','Passwort / password',1)}
  <h3 style="font-size:13px">RetroAchievements</h3>${fld('ra_key','API-Key',1)}
  <div class=frow><span class=meta id=rastat style="flex:1">…</span>
   <button type=button onclick="raRefresh()" style="background:#2a2f37">${t('ra_refresh')}</button></div>
  <h3 style="font-size:13px">${t('stream_title')}</h3>
  <div class=meta style="font-size:11px;margin-bottom:4px">${t('stream_hint')}</div>
  ${fld('stream_url',t('stream_url_l'))}${fld('stream_launch',t('stream_launch_l'),1)}
  <div class=frow><span class=meta id=emustat style="flex:1">…</span>
   <button type=button onclick="emuUpdate()" style="background:#2a2f37">${t('emu_update')}</button></div>
  <h3 style="font-size:13px">${t('cat_title')}</h3>
  <div class=meta style="font-size:11px;margin-bottom:4px">${t('cat_hint')}</div>
  <div class=frow><label style="min-width:150px">${t('cat_urls')}</label>
   <textarea id=c_catalog_urls style="flex:1;min-height:60px;background:#0b0d10;border:1px solid #2c323b;color:#e6e8ec;padding:6px;border-radius:6px;font-family:ui-monospace,monospace;font-size:11px">${(vals['catalog_urls']||'').replace(/</g,'&lt;')}</textarea></div>
  <div class=frow><span class=meta id=catstat style="flex:1">…</span>
   <button type=button onclick="catRefresh()" style="background:#2a2f37">${t('cat_refresh')}</button></div>
  <h3 style="font-size:13px">JDownloader</h3>
  <div class=meta style="font-size:11px;margin-bottom:4px">${t('jd_hint')}</div>
  ${fld('jd_watch',t('jd_watch'))}${fld('jd_out',t('jd_out'))}${fld('jd_dl_base',t('jd_base'))}
  <div class=frow><button onclick="saveConn()">${t('save')}</button><button onclick="testConn()" style="margin-left:8px;background:#2a2f37">${t('test')}</button><span id=cmsg class=meta></span></div>
  <div id=csvc style="margin-top:10px"></div>`;raStatus();catStatus();emuStatus();}
// --- Emulatoren auf dem Streaming-Host: Stand + Aktualisierung (#71) ---
async function emuStatus(){let el=document.getElementById('emustat');if(!el)return;
 let d={};try{d=await(await fetch('/api/stream/emulators')).json();}catch(e){el.textContent=t('emu_nohost');return;}
 if(!d.ok){el.textContent=d.reason==='no_launcher'?t('emu_nolauncher'):t('emu_unreachable');return;}
 if(d.running){el.textContent=t('emu_running');setTimeout(emuStatus,5000);return;}
 // Je Emulator die Fassung — und, wo eine vorige aufgehoben wurde, den Rueckweg.
 let liste=(d.emulators||[]).map(e=>{
   let v=e.version?' <span class=meta>('+e.version.replace(/</g,'&lt;')+')</span>':'';
   let rb=e.can_rollback
     ?` <a href="#" onclick="emuRollback('${e.name}');return false" title="${(e.previous||'').replace(/"/g,'')}" style="color:#d29922">↩</a>`
     :'';
   return e.name+v+rb;}).join(' · ');
 el.innerHTML=(liste?liste:t('emu_none'))
  +(d.rc!==null&&d.rc!==undefined?'<br><span class=meta>'+(d.rc===0?t('emu_ok'):t('emu_failed'))+'</span>':'');}
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
async function secNotif(c){let s=await(await fetch('/api/settings')).json();let dc=s.discord||{};let sm=s.smtp||{};let ag=s.agents||{};
 c.innerHTML=`<h3>${t('notif_discord')}</h3>
  <div class=frow><label style="min-width:auto"><input type=checkbox id=dcen ${dc.enabled?'checked':''}> ${t('active')}</label><span></span></div>
  <div class=frow><input id=dcurl placeholder="${t('webhook_ph')}" value="${(dc.url||'').replace(/"/g,'&quot;')}"><button onclick="testNotify()">${t('test')}</button></div>
  <div class=frow><button onclick="saveSettings()">${t('save')}</button><span id=serr class=meta></span></div>
  <h3 style="margin-top:20px">E-Mail (SMTP)</h3>
  <div class=frow><label style="min-width:auto"><input type=checkbox id=smen ${sm.enabled?'checked':''}> ${t('active')}</label><span></span></div>
  <div class=frow><input id=smhost placeholder="Host" value="${(sm.host||'').replace(/"/g,'&quot;')}"><input id=smport placeholder="Port" style="flex:0 0 80px" value="${sm.port||'587'}"></div>
  <div class=frow><input id=smuser placeholder="User" value="${(sm.user||'').replace(/"/g,'&quot;')}"><input id=smpass type=password placeholder="${sm.has_pass?'•••• gesetzt':'Passwort'}"></div>
  <div class=frow><input id=smfrom placeholder="Absender / From" value="${(sm.from||'').replace(/"/g,'&quot;')}"><select id=smtls style="flex:0 0 120px"><option value=starttls ${sm.tls=='starttls'?'selected':''}>STARTTLS</option><option value=ssl ${sm.tls=='ssl'?'selected':''}>SSL</option><option value=none ${sm.tls=='none'?'selected':''}>none</option></select></div>
  <div class=frow><input id=smto placeholder="Test an / to"><button onclick="mailTest()">${t('test')}</button></div>
  <div class=frow><button onclick="saveSmtp()">${t('save')}</button><span id=smmsg class=meta></span></div>
  <h3 style="margin-top:20px">Weitere Agenten / More agents</h3>
  <div class=frow><label style="min-width:auto"><input type=checkbox id=agem ${(ag.email||{}).enabled?'checked':''}> E-Mail bei Verfügbarkeit / email on availability</label><span></span></div>
  <div class=frow><label style="min-width:auto"><input type=checkbox id=agtgen ${(ag.telegram||{}).enabled?'checked':''}> Telegram</label><span></span></div>
  <div class=frow><input id=agtgtok type=password placeholder="${(ag.telegram||{}).has_token?'•••• Token gesetzt':'Bot-Token'}"><input id=agtgchat placeholder="Chat-ID" value="${((ag.telegram||{}).chat||'').replace(/"/g,'&quot;')}"></div>
  <div class=frow><label style="min-width:auto"><input type=checkbox id=agwhen ${(ag.webhook||{}).enabled?'checked':''}> Webhook (generisch / Slack-kompatibel)</label><span></span></div>
  <div class=frow><input id=agwhurl placeholder="Webhook-URL" value="${((ag.webhook||{}).url||'').replace(/"/g,'&quot;')}"></div>
  <div class=frow><label style="min-width:auto"><input type=checkbox id=aggoen ${(ag.gotify||{}).enabled?'checked':''}> Gotify</label><span></span></div>
  <div class=frow><input id=aggourl placeholder="Gotify-URL (https://gotify.host)" value="${((ag.gotify||{}).url||'').replace(/"/g,'&quot;')}"><input id=aggotok type=password placeholder="${(ag.gotify||{}).has_token?'•••• App-Token gesetzt':'App-Token'}"></div>
  <div class=frow><label style="min-width:auto"><input type=checkbox id=agnten ${(ag.ntfy||{}).enabled?'checked':''}> ntfy</label><span></span></div>
  <div class=frow><input id=agnturl placeholder="ntfy-URL (Standard https://ntfy.sh)" value="${((ag.ntfy||{}).url||'').replace(/"/g,'&quot;')}"><input id=agnttopic placeholder="Topic" style="flex:0 0 160px" value="${((ag.ntfy||{}).topic||'').replace(/"/g,'&quot;')}"><input id=agnttok type=password placeholder="${(ag.ntfy||{}).has_token?'•••• Token':'Token (optional)'}"></div>
  <div class=frow><label style="min-width:auto"><input type=checkbox id=agpoen ${(ag.pushover||{}).enabled?'checked':''}> Pushover</label><span></span></div>
  <div class=frow><input id=agpouser placeholder="User-Key" value="${((ag.pushover||{}).user||'').replace(/"/g,'&quot;')}"><input id=agpotok type=password placeholder="${(ag.pushover||{}).has_token?'•••• App-Token gesetzt':'App-Token'}"></div>
  <div class=frow><button onclick="saveAgents()">${t('save')}</button><button onclick="testAgents()" style="margin-left:8px;background:#2a2f37">${t('test')}</button><span id=agmsg class=meta></span></div>
  <h3 style="margin-top:20px">Mail-Protokoll / Mail log</h3><div id=mlog class=meta>…</div>`;
 let ml=await(await fetch('/api/maillog')).json();
 document.getElementById('mlog').innerHTML=ml.length?ml.map(m=>`<div class=frow><span>${m.ok?'🟢':'🔴'} ${m.ts} → ${(''+(m.to||'')).replace(/</g,'&lt;')}</span><span class=meta>${(''+(m.subject||'')).replace(/</g,'&lt;')}${m.err?(' · '+(''+m.err).replace(/</g,'&lt;')):''}</span></div>`).join(''):'—';}
async function saveSmtp(){let d={smtp:{enabled:document.getElementById('smen').checked,host:document.getElementById('smhost').value,port:document.getElementById('smport').value,user:document.getElementById('smuser').value,from:document.getElementById('smfrom').value,tls:document.getElementById('smtls').value}};
 let pw=document.getElementById('smpass').value;if(pw)d.smtp.pass=pw;
 let r=await(await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 document.getElementById('smmsg').textContent=r.ok?t('saved_ok'):t('st_error');return r.ok;}
async function mailTest(){let to=document.getElementById('smto').value.trim();if(!to)return;await saveSmtp();
 let r=await(await fetch('/api/settings/mail-test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({to:to})})).json();
 document.getElementById('smmsg').textContent=r.ok?t('test_sent'):(r.msg||t('st_error'));}
async function saveAgents(){let d={agents:{email:{enabled:document.getElementById('agem').checked},
  telegram:{enabled:document.getElementById('agtgen').checked,chat:document.getElementById('agtgchat').value},
  webhook:{enabled:document.getElementById('agwhen').checked,url:document.getElementById('agwhurl').value},
  gotify:{enabled:document.getElementById('aggoen').checked,url:document.getElementById('aggourl').value},
  ntfy:{enabled:document.getElementById('agnten').checked,url:document.getElementById('agnturl').value,topic:document.getElementById('agnttopic').value},
  pushover:{enabled:document.getElementById('agpoen').checked,user:document.getElementById('agpouser').value}}};
 let tok=document.getElementById('agtgtok').value;if(tok)d.agents.telegram.token=tok;
 let got=document.getElementById('aggotok').value;if(got)d.agents.gotify.token=got;
 let ntt=document.getElementById('agnttok').value;if(ntt)d.agents.ntfy.token=ntt;
 let pot=document.getElementById('agpotok').value;if(pot)d.agents.pushover.token=pot;
 let r=await(await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
 document.getElementById('agmsg').textContent=r.ok?t('saved_ok'):t('st_error');return r.ok;}
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
 c.innerHTML=`<h3>${t('blocklist')}</h3><div id=bllist></div>
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
document.querySelectorAll('#langsw b').forEach(e=>e.classList.toggle('on',e.dataset.l==LANG));
applyI18n();loadAuth();loadPlatforms();loadDiscover();updateMsgBadge();
if('serviceWorker'in navigator){navigator.serviceWorker.register('/sw.js').catch(()=>{});}
document.getElementById('q').addEventListener('keydown',e=>{if(e.key=='Enter')search();});
setInterval(()=>{if(cur=='j')loadJobs();},4000);
