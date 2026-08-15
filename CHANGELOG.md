# Changelog

Alle nennenswerten Änderungen an diesem Projekt. Format nach
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung nach [SemVer](https://semver.org/lang/de/).

## [1.5.0](https://github.com/Sparxx947/romseerr/compare/v1.4.3...v1.5.0) (2026-08-15)


### Neu / Features

* **brand:** draw every menu and settings-tab icon, outline style ([#700](https://github.com/Sparxx947/romseerr/issues/700)) ([80008cb](https://github.com/Sparxx947/romseerr/commit/80008cbc0b314a2a94e7ffd27ce5e0b9e41be7fb))
* **brand:** give Romseerr a drawn mark instead of an emoji ([#651](https://github.com/Sparxx947/romseerr/issues/651)) ([fc20f6a](https://github.com/Sparxx947/romseerr/commit/fc20f6aabc4f274564abeb938fee687f6190510b)), closes [#650](https://github.com/Sparxx947/romseerr/issues/650)
* **import:** show what landed in .unsortiert ([#674](https://github.com/Sparxx947/romseerr/issues/674)) ([f4e61a9](https://github.com/Sparxx947/romseerr/commit/f4e61a9db9271bafeb3df5a553f441de7d684315)), closes [#656](https://github.com/Sparxx947/romseerr/issues/656)
* **notify:** let web push be tested, and make the test able to fail ([#686](https://github.com/Sparxx947/romseerr/issues/686)) ([c4580dd](https://github.com/Sparxx947/romseerr/commit/c4580dd2795e4be0bb027443dc8193c0eded6bb0)), closes [#684](https://github.com/Sparxx947/romseerr/issues/684)
* **notify:** make notifications selectable per event, on two levels ([#716](https://github.com/Sparxx947/romseerr/issues/716)) ([5250540](https://github.com/Sparxx947/romseerr/commit/525054056e6da200da2d1f2ec4dc1ccbe2eec055))
* **quota:** measure volume as well as count, and allow a per-user limit ([#715](https://github.com/Sparxx947/romseerr/issues/715)) ([54c82f2](https://github.com/Sparxx947/romseerr/commit/54c82f2670d4a57f4876bb3052fa07ac28756384))
* **search:** add back and clear buttons to the search row ([#679](https://github.com/Sparxx947/romseerr/issues/679)) ([b8c86fb](https://github.com/Sparxx947/romseerr/commit/b8c86fbfaff7577e07c4d369a3c9d249ab024a80)), closes [#661](https://github.com/Sparxx947/romseerr/issues/661)
* **ui:** draw the in-library badge in the mark's language, per theme ([#696](https://github.com/Sparxx947/romseerr/issues/696)) ([713e8fa](https://github.com/Sparxx947/romseerr/commit/713e8faa8b476fb6cd85d975feadeb2e7fbf658b))
* **ui:** fourth theme 'aurora' — top navigation, hero, aurora gradient ([#630](https://github.com/Sparxx947/romseerr/issues/630)) ([ce50ee3](https://github.com/Sparxx947/romseerr/commit/ce50ee3fdfd50167f56e9f501c660a0772d7208c)), closes [#629](https://github.com/Sparxx947/romseerr/issues/629)
* **ui:** give warning and error their own per-theme variables ([#704](https://github.com/Sparxx947/romseerr/issues/704)) ([a3ee2a1](https://github.com/Sparxx947/romseerr/commit/a3ee2a138ee2c2bc79bb548ee0be2483a60242da))
* **ui:** make the mark a link back to the start page ([#670](https://github.com/Sparxx947/romseerr/issues/670)) ([6cb9690](https://github.com/Sparxx947/romseerr/commit/6cb96907f4b3e736a31ab50a0393becdbeb2a870))
* **ui:** map the JavaScript's hard-coded palette onto theme variables ([#706](https://github.com/Sparxx947/romseerr/issues/706)) ([4f139bc](https://github.com/Sparxx947/romseerr/commit/4f139bc8255c263105102f691ce5e9006957166f))
* **ui:** move the language picker and user menu into the navigation under Aurora ([#678](https://github.com/Sparxx947/romseerr/issues/678)) ([7b69ffe](https://github.com/Sparxx947/romseerr/commit/7b69ffe8b0b7967401ab717905bd8b7c88538ef8)), closes [#672](https://github.com/Sparxx947/romseerr/issues/672)
* **ui:** replace the 8 native confirm() dialogs with a themed one ([#642](https://github.com/Sparxx947/romseerr/issues/642)) ([691441f](https://github.com/Sparxx947/romseerr/commit/691441f99d2444e3fbabb1d8b6ce49fb2dcff4eb)), closes [#641](https://github.com/Sparxx947/romseerr/issues/641)


### Behoben / Fixes

* **brand:** size the mark on the login and reset pages ([#653](https://github.com/Sparxx947/romseerr/issues/653)) ([8436d8e](https://github.com/Sparxx947/romseerr/commit/8436d8e0fc326640f1cba86ea787144e965cd08d)), closes [#652](https://github.com/Sparxx947/romseerr/issues/652)
* **http:** serve HTML entry points with no-cache ([#644](https://github.com/Sparxx947/romseerr/issues/644)) ([ac4c90b](https://github.com/Sparxx947/romseerr/commit/ac4c90bc91fc772808c0ea0fed22f4b3b4ed87ea)), closes [#643](https://github.com/Sparxx947/romseerr/issues/643)
* **i18n:** stop gluing the count to a plural noun ([#676](https://github.com/Sparxx947/romseerr/issues/676)) ([ba2a3cf](https://github.com/Sparxx947/romseerr/commit/ba2a3cfc140d9f6d1bb0263657c82c19c894b864)), closes [#675](https://github.com/Sparxx947/romseerr/issues/675)
* **import:** replace the wrong extension instead of appending to it ([#673](https://github.com/Sparxx947/romseerr/issues/673)) ([b08ebf8](https://github.com/Sparxx947/romseerr/commit/b08ebf8372ccfc689f9fb5935f1f9cb442be6449)), closes [#649](https://github.com/Sparxx947/romseerr/issues/649)
* **leftovers:** surface why a removal failed instead of reporting zero ([#646](https://github.com/Sparxx947/romseerr/issues/646)) ([693e1fb](https://github.com/Sparxx947/romseerr/commit/693e1fb8cb1610e096299afc7f51a54e126d6026)), closes [#645](https://github.com/Sparxx947/romseerr/issues/645)
* **library:** name the four counts correctly instead of calling three of them the same ([#680](https://github.com/Sparxx947/romseerr/issues/680)) ([9db374e](https://github.com/Sparxx947/romseerr/commit/9db374e818719a010279fb0ea0f674484fc57288)), closes [#654](https://github.com/Sparxx947/romseerr/issues/654)
* **library:** the load path had the same mislabelling as the rebuild ([#681](https://github.com/Sparxx947/romseerr/issues/681)) ([1bef173](https://github.com/Sparxx947/romseerr/commit/1bef17377ce9cc2430263de330155203d3c90301))
* **search:** count and send the bulk request by group state too ([#695](https://github.com/Sparxx947/romseerr/issues/695)) ([dccd4be](https://github.com/Sparxx947/romseerr/commit/dccd4beaeca7b82fe2fb78f9f58c199345c7ffe4))
* **search:** one card per game instead of one per release ([#694](https://github.com/Sparxx947/romseerr/issues/694)) ([2f30c74](https://github.com/Sparxx947/romseerr/commit/2f30c740c607d6597d2ba02d124cd9cded74151a))
* **search:** say in the result list what the platform filter is holding back ([#692](https://github.com/Sparxx947/romseerr/issues/692)) ([96fb9ec](https://github.com/Sparxx947/romseerr/commit/96fb9ec815b5a70f67e26f29de53d6a4516a8390))
* **search:** size only marks a collection on cartridge-era platforms ([#690](https://github.com/Sparxx947/romseerr/issues/690)) ([77ba186](https://github.com/Sparxx947/romseerr/commit/77ba1867b1902ae8d8a36e1d5e6cf2ee76fa97f7)), closes [#689](https://github.com/Sparxx947/romseerr/issues/689)
* **stream:** describe VirtualGL as it actually is — wrapper set, Vulkan bypassing it ([#683](https://github.com/Sparxx947/romseerr/issues/683)) ([eeee679](https://github.com/Sparxx947/romseerr/commit/eeee6790e0eeab1ffc8b099593b1605a1bfa70f6)), closes [#628](https://github.com/Sparxx947/romseerr/issues/628)
* **ui:** base styling for buttons, selects and textareas ([#640](https://github.com/Sparxx947/romseerr/issues/640)) ([fcd9d7c](https://github.com/Sparxx947/romseerr/commit/fcd9d7c934df26869b2c059c06f4e7f7b2977613)), closes [#639](https://github.com/Sparxx947/romseerr/issues/639)
* **ui:** carry the Aurora glow across the header edge ([#664](https://github.com/Sparxx947/romseerr/issues/664)) ([ad5363b](https://github.com/Sparxx947/romseerr/commit/ad5363bb233e9cdfcde1385c42eab465dfcaac66)), closes [#657](https://github.com/Sparxx947/romseerr/issues/657)
* **ui:** centre the × in the modal close button ([#663](https://github.com/Sparxx947/romseerr/issues/663)) ([11fe8a2](https://github.com/Sparxx947/romseerr/commit/11fe8a26b88e792cbe37b74491843575f896caea)), closes [#659](https://github.com/Sparxx947/romseerr/issues/659)
* **ui:** derive the platform from the library instead of saying "unknown" ([#687](https://github.com/Sparxx947/romseerr/issues/687)) ([7f7d488](https://github.com/Sparxx947/romseerr/commit/7f7d488b66458bb9c4483496b268d92123cf5c64)), closes [#685](https://github.com/Sparxx947/romseerr/issues/685)
* **ui:** give the three detail-card buttons one class and drawn icons ([#709](https://github.com/Sparxx947/romseerr/issues/709)) ([3e35e2e](https://github.com/Sparxx947/romseerr/commit/3e35e2e01c8beb851d2533434e736643b841cf1b))
* **ui:** hide the aurora hero outside discover, and match the request buttons ([#637](https://github.com/Sparxx947/romseerr/issues/637)) ([aea9a32](https://github.com/Sparxx947/romseerr/commit/aea9a328bcc50b788ecf2907a658634ddd0c8ec0)), closes [#636](https://github.com/Sparxx947/romseerr/issues/636)
* **ui:** label a recommendation row the same in both places ([#633](https://github.com/Sparxx947/romseerr/issues/633)) ([8957090](https://github.com/Sparxx947/romseerr/commit/89570900551b619754a8ca1f7983ab272b7aa481)), closes [#632](https://github.com/Sparxx947/romseerr/issues/632)
* **ui:** let the danger button class win against the ID rules that paint by context ([#648](https://github.com/Sparxx947/romseerr/issues/648)) ([68c3d75](https://github.com/Sparxx947/romseerr/commit/68c3d753fbffaf5438bb4534d76ff5e1ada979d0)), closes [#647](https://github.com/Sparxx947/romseerr/issues/647)
* **ui:** make a click on a request title reach the card ([#677](https://github.com/Sparxx947/romseerr/issues/677)) ([676d23a](https://github.com/Sparxx947/romseerr/commit/676d23a4131f1bb0923a5914ac54802ff16b137a)), closes [#638](https://github.com/Sparxx947/romseerr/issues/638)
* **ui:** make the in-library drawing fill its box so the chamfer survives ([#697](https://github.com/Sparxx947/romseerr/issues/697)) ([52d5985](https://github.com/Sparxx947/romseerr/commit/52d598523778244ab356995c57768dd497b47272))
* **ui:** make the navigation column width one value instead of three copies ([#711](https://github.com/Sparxx947/romseerr/issues/711)) ([90a31bd](https://github.com/Sparxx947/romseerr/commit/90a31bdd5ec186fc826d0cc8c390d1593599c649))
* **ui:** move the seven remaining greens in the JavaScript onto the theme ([#701](https://github.com/Sparxx947/romseerr/issues/701)) ([33c1d9f](https://github.com/Sparxx947/romseerr/commit/33c1d9f73b28ffea5ac762f04e2e6f27f0d18376))
* **ui:** scope the absolute badge to covers so the play button stays in the card ([#702](https://github.com/Sparxx947/romseerr/issues/702)) ([beb025b](https://github.com/Sparxx947/romseerr/commit/beb025bd06d0ff3b895661e0e751c8a47e193318))
* **ui:** style the scrollbars from the design variables ([#635](https://github.com/Sparxx947/romseerr/issues/635)) ([1da7a17](https://github.com/Sparxx947/romseerr/commit/1da7a1750b6f089347ae34e5477c25e755f1187e)), closes [#634](https://github.com/Sparxx947/romseerr/issues/634)


### Leistung / Performance

* **import:** re-read only the platforms an import wrote to ([#665](https://github.com/Sparxx947/romseerr/issues/665)) ([025a998](https://github.com/Sparxx947/romseerr/commit/025a998091ff1001ba040903b5ce0c8a8b7fbb30))
* **index:** ask the filesystem in parallel, not one file after another ([#666](https://github.com/Sparxx947/romseerr/issues/666)) ([#671](https://github.com/Sparxx947/romseerr/issues/671)) ([ead8be8](https://github.com/Sparxx947/romseerr/commit/ead8be8afb0ad8fa3566d55e2f58806652aea8bd))


### Dokumentation / Documentation

* add interface screenshots to both READMEs ([#707](https://github.com/Sparxx947/romseerr/issues/707)) ([7cc5cda](https://github.com/Sparxx947/romseerr/commit/7cc5cda2f06aae3a3c34615884d80a174d9bb247))
* **css:** correct the colour claim on the platform-filter notice ([#693](https://github.com/Sparxx947/romseerr/issues/693)) ([20d2b8b](https://github.com/Sparxx947/romseerr/commit/20d2b8bb2078f3a95656dd1e5b71fff1e5fdb647))
* **stream:** say that VirtualGL is unused instead of describing it as the path ([#682](https://github.com/Sparxx947/romseerr/issues/682)) ([f888de4](https://github.com/Sparxx947/romseerr/commit/f888de4cc766e10887074783df9b07a2fa0dce14)), closes [#628](https://github.com/Sparxx947/romseerr/issues/628)

## [1.4.3](https://github.com/Sparxx947/romseerr/compare/v1.4.2...v1.4.3) (2026-08-14)


### Behoben / Fixes

* **ui:** say when a hit has no platform instead of printing a question mark ([#622](https://github.com/Sparxx947/romseerr/issues/622)) ([44a2c17](https://github.com/Sparxx947/romseerr/commit/44a2c17b2bd76f784ab3fb6974a6f73b6a5dca2b)), closes [#621](https://github.com/Sparxx947/romseerr/issues/621)

## [1.4.2](https://github.com/Sparxx947/romseerr/compare/v1.4.1...v1.4.2) (2026-08-14)


### Behoben / Fixes

* **dedup:** make the comparison key identify the same game again ([#619](https://github.com/Sparxx947/romseerr/issues/619)) ([44a537f](https://github.com/Sparxx947/romseerr/commit/44a537fdd73d4b2ed735a7a8b5dc1ed9ac21b04a)), closes [#616](https://github.com/Sparxx947/romseerr/issues/616)

## [1.4.1](https://github.com/Sparxx947/romseerr/compare/v1.4.0...v1.4.1) (2026-08-14)


### Behoben / Fixes

* **import:** keep the internal job prefix out of library filenames ([#613](https://github.com/Sparxx947/romseerr/issues/613)) ([#614](https://github.com/Sparxx947/romseerr/issues/614)) ([865bb38](https://github.com/Sparxx947/romseerr/commit/865bb38a21faaf31b9890c03cb1f3ee8ac365639))
* **import:** recognise a ROM by its magic when the name gives nothing ([#611](https://github.com/Sparxx947/romseerr/issues/611)) ([#612](https://github.com/Sparxx947/romseerr/issues/612)) ([4edf1de](https://github.com/Sparxx947/romseerr/commit/4edf1de8f3ed8544cf234657a0be68abda8403b5))
* **jobs:** ask SAB before handing it the same NZB again ([#609](https://github.com/Sparxx947/romseerr/issues/609)) ([#610](https://github.com/Sparxx947/romseerr/issues/610)) ([a88c5d4](https://github.com/Sparxx947/romseerr/commit/a88c5d4f4fbb8599be61864f6d0b3ebc4f0c32ed))
* **search:** drop PS5 and Xbox Series hits instead of calling them Switch ([#607](https://github.com/Sparxx947/romseerr/issues/607)) ([#608](https://github.com/Sparxx947/romseerr/issues/608)) ([44488ba](https://github.com/Sparxx947/romseerr/commit/44488ba2ca64eb556a1f5cdb6bfb909d35d21c45))
* **test:** a vanishing onboarding tour no longer fails the browser suite ([#603](https://github.com/Sparxx947/romseerr/issues/603)) ([#604](https://github.com/Sparxx947/romseerr/issues/604)) ([0f248c7](https://github.com/Sparxx947/romseerr/commit/0f248c7f67e5a219d1285f1948a2e1bbd8fbddc9))

## [1.4.0](https://github.com/Sparxx947/romseerr/compare/v1.3.0-beta.1...v1.4.0) (2026-08-14)


### Neu / Features

* **library-tools:** --nur-beiwerk sammelt ein, ohne den ganzen Umbau zu fahren ([#318](https://github.com/Sparxx947/romseerr/issues/318)) ([#580](https://github.com/Sparxx947/romseerr/issues/580)) ([f5d764d](https://github.com/Sparxx947/romseerr/commit/f5d764df22ad0d2cb2fd440c737e0fa9bdb12e40))
* **ui:** show what the library rebuild is doing, in the settings ([#593](https://github.com/Sparxx947/romseerr/issues/593)) ([#594](https://github.com/Sparxx947/romseerr/issues/594)) ([75a4b17](https://github.com/Sparxx947/romseerr/commit/75a4b1739bd6211a2828a13e39345c55e66df65e))
* **ui:** start and stop library rebuilds from the settings ([#593](https://github.com/Sparxx947/romseerr/issues/593)) ([#596](https://github.com/Sparxx947/romseerr/issues/596)) ([4065af6](https://github.com/Sparxx947/romseerr/commit/4065af602cdbefd91709b6c1afa4dfc96e3832c1))


### Behoben / Fixes

* **app:** der Update-Hinweis unterscheidet jetzt zwei Betas derselben Version ([#574](https://github.com/Sparxx947/romseerr/issues/574)) ([#576](https://github.com/Sparxx947/romseerr/issues/576)) ([c07c63d](https://github.com/Sparxx947/romseerr/commit/c07c63dc40d42dcbb7bdc95d7133a9bbc2119648))
* **app:** drop two calls deprecated on the Python the image actually runs ([#588](https://github.com/Sparxx947/romseerr/issues/588)) ([#591](https://github.com/Sparxx947/romseerr/issues/591)) ([36769e2](https://github.com/Sparxx947/romseerr/commit/36769e2a8358d634a5c0def72f6ae7d1a2c8241e))
* **app:** report a session key that cannot be saved instead of minting a new one ([#587](https://github.com/Sparxx947/romseerr/issues/587)) ([#590](https://github.com/Sparxx947/romseerr/issues/590)) ([da66f61](https://github.com/Sparxx947/romseerr/commit/da66f6139b8141847f626abacd60cd5f0baa3441))
* **ci:** bring main's stray dependency bump back into dev ([#563](https://github.com/Sparxx947/romseerr/issues/563)) ([e782534](https://github.com/Sparxx947/romseerr/commit/e782534f45af1421e7f3231599c4efabfb1966b7))
* **ci:** bring main's stray dependency bump back into dev ([#563](https://github.com/Sparxx947/romseerr/issues/563)) ([b21eaf3](https://github.com/Sparxx947/romseerr/commit/b21eaf3178a68de2d26ceeaa9f4c5dbcc6247c19))
* **ci:** mark beta releases as pre-releases, and keep the update check working ([#572](https://github.com/Sparxx947/romseerr/issues/572)) ([#573](https://github.com/Sparxx947/romseerr/issues/573)) ([d2db0fb](https://github.com/Sparxx947/romseerr/commit/d2db0fb134ac10b3b1b96101b53319c0499ebabd))
* **library-tools:** a progress file with the wrong shape no longer kills the run ([#583](https://github.com/Sparxx947/romseerr/issues/583)) ([#584](https://github.com/Sparxx947/romseerr/issues/584)) ([28407d5](https://github.com/Sparxx947/romseerr/commit/28407d5c5fb9c00e43a4f70ef22324d3473b9dbc))
* **library-tools:** ein Trockenlauf hinterlaesst keinen Wiederaufsetzpunkt ([#581](https://github.com/Sparxx947/romseerr/issues/581)) ([#582](https://github.com/Sparxx947/romseerr/issues/582)) ([2603126](https://github.com/Sparxx947/romseerr/commit/2603126ea169b621027bf029c9dfcdcd38f4fb43))
* **library-tools:** Musik und Symbole zaehlen nicht als Spiele ([#318](https://github.com/Sparxx947/romseerr/issues/318)) ([#579](https://github.com/Sparxx947/romseerr/issues/579)) ([432f917](https://github.com/Sparxx947/romseerr/commit/432f917c7c48c26741e2906e268c80c5e10a9077))
* **library-tools:** recognise extensionless ancillary files by signature ([#318](https://github.com/Sparxx947/romseerr/issues/318)) ([#598](https://github.com/Sparxx947/romseerr/issues/598)) ([b6017dd](https://github.com/Sparxx947/romseerr/commit/b6017ddaaf90a723e9e576dc38da9301f89851f9))
* **ui:** a finished rebuild shows how long it took, not how long ago it started ([#593](https://github.com/Sparxx947/romseerr/issues/593)) ([#595](https://github.com/Sparxx947/romseerr/issues/595)) ([21dd371](https://github.com/Sparxx947/romseerr/commit/21dd37187c5bffc78fc4146d2f925f747d58ceb0))
* **ui:** der Update-Hinweis verlinkt die Version, die er nennt ([#577](https://github.com/Sparxx947/romseerr/issues/577)) ([#578](https://github.com/Sparxx947/romseerr/issues/578)) ([3f5c2b7](https://github.com/Sparxx947/romseerr/commit/3f5c2b7cb43cfed397e527115e5615f9e00d1d79))
* **ui:** keep a finished run visible, because that is when its result exists ([#593](https://github.com/Sparxx947/romseerr/issues/593)) ([#597](https://github.com/Sparxx947/romseerr/issues/597)) ([f39a15b](https://github.com/Sparxx947/romseerr/commit/f39a15b4289a2b6ee3a6e3b3fe44639b9f8cc098))


### Sonstiges / Chores

* **release:** publish 1.4.0 as the first stable release ([#600](https://github.com/Sparxx947/romseerr/issues/600)) ([#601](https://github.com/Sparxx947/romseerr/issues/601)) ([62cdec8](https://github.com/Sparxx947/romseerr/commit/62cdec882ceab88af12bae2291910927a9d3a95c))

## [1.3.0-beta.1](https://github.com/Sparxx947/romseerr/compare/v1.2.0-beta.1...v1.3.0-beta.1) (2026-08-13)


### Neu / Features

* **library:** the sorter knows the Aquarius cassette format ([#515](https://github.com/Sparxx947/romseerr/issues/515)) ([#516](https://github.com/Sparxx947/romseerr/issues/516)) ([9096979](https://github.com/Sparxx947/romseerr/commit/9096979ceda016c2bc864364925fa3f3cda925a0))
* **library:** tool to check disc image lists against their data files ([#466](https://github.com/Sparxx947/romseerr/issues/466)) ([9be901e](https://github.com/Sparxx947/romseerr/commit/9be901e1baad6414e060766a0ff66dc9cc94d4f0)), closes [#465](https://github.com/Sparxx947/romseerr/issues/465)
* **play:** Neo Geo CD is its own platform, because RomM keeps it separate ([#518](https://github.com/Sparxx947/romseerr/issues/518)) ([#523](https://github.com/Sparxx947/romseerr/issues/523)) ([6b14b9e](https://github.com/Sparxx947/romseerr/commit/6b14b9ed51e062585b42c969166b0ac0c8c96339))
* **stream:** Cemu had no gamepad mapping at all, and three platforms were still marked untested ([#304](https://github.com/Sparxx947/romseerr/issues/304)) ([#560](https://github.com/Sparxx947/romseerr/issues/560)) ([5bc90af](https://github.com/Sparxx947/romseerr/commit/5bc90afa55153861708d9583caab9df37c07aa2f))
* **stream:** Flycast gets its renderer written, not only passed ([#304](https://github.com/Sparxx947/romseerr/issues/304)) ([#533](https://github.com/Sparxx947/romseerr/issues/533)) ([b1a2bdb](https://github.com/Sparxx947/romseerr/commit/b1a2bdba2ab347dad087ca7bee90d0549f1d013b))
* **stream:** launch Flycast in fullscreen on Vulkan ([#461](https://github.com/Sparxx947/romseerr/issues/461)) ([bbe8462](https://github.com/Sparxx947/romseerr/commit/bbe846243341676162d9da4cb21697291d6f573d))
* **stream:** PS3 firmware installs without a click — the flag is --headless ([#164](https://github.com/Sparxx947/romseerr/issues/164)) ([#562](https://github.com/Sparxx947/romseerr/issues/562)) ([b28ce46](https://github.com/Sparxx947/romseerr/commit/b28ce460cf9b1845a54d8257a55a093fe2ea21d9))
* **stream:** record what else the host was doing at launch ([#527](https://github.com/Sparxx947/romseerr/issues/527)) ([#528](https://github.com/Sparxx947/romseerr/issues/528)) ([33b4483](https://github.com/Sparxx947/romseerr/commit/33b4483b4c702826c654b703077060c805074d4a))
* **stream:** start Vita3K titles in fullscreen ([#474](https://github.com/Sparxx947/romseerr/issues/474)) ([40263c4](https://github.com/Sparxx947/romseerr/commit/40263c4c0810731d4790c6fb457a7fc0a4aa1c96)), closes [#304](https://github.com/Sparxx947/romseerr/issues/304)


### Behoben / Fixes

* **import:** recognise a PS Vita title folder instead of taking its eboot.bin ([#456](https://github.com/Sparxx947/romseerr/issues/456)) ([0254546](https://github.com/Sparxx947/romseerr/commit/025454689c81402ef40a35c06005483199171196)), closes [#455](https://github.com/Sparxx947/romseerr/issues/455)
* **import:** write into the folder that already holds the platform ([#457](https://github.com/Sparxx947/romseerr/issues/457)) ([633acaa](https://github.com/Sparxx947/romseerr/commit/633acaaa8bf9daaba39dca82b6ee0a2bfa0c9975)), closes [#454](https://github.com/Sparxx947/romseerr/issues/454)
* **index:** a folder title is one title, not its contents ([#478](https://github.com/Sparxx947/romseerr/issues/478)) ([b1659bd](https://github.com/Sparxx947/romseerr/commit/b1659bdcd54fd112108e301090cd5bc76560e9f6)), closes [#477](https://github.com/Sparxx947/romseerr/issues/477)
* **library-tools:** a reference without an extension can now be solved ([#517](https://github.com/Sparxx947/romseerr/issues/517)) ([#519](https://github.com/Sparxx947/romseerr/issues/519)) ([adbcc84](https://github.com/Sparxx947/romseerr/commit/adbcc84b9f65c13cf7a60a71e9a785865045ed4b))
* **library-tools:** give the extraction target a collision-free name ([#444](https://github.com/Sparxx947/romseerr/issues/444)) ([a744e7d](https://github.com/Sparxx947/romseerr/commit/a744e7d8b7a901e4a62d45e83114254491409284))
* **library-tools:** the rewrite replaced each reference twice ([#521](https://github.com/Sparxx947/romseerr/issues/521)) ([#522](https://github.com/Sparxx947/romseerr/issues/522)) ([891f93b](https://github.com/Sparxx947/romseerr/commit/891f93b7c15bfebeb61b8df00a0b0dc5c7ba759d))
* **library-tools:** unpack RAR, LZH and LHA instead of leaving them closed ([#448](https://github.com/Sparxx947/romseerr/issues/448)) ([1c4bfeb](https://github.com/Sparxx947/romseerr/commit/1c4bfeb42120be517e7add2ab02eb7d327eaaec0))
* **library:** a disc-image set is one game, not a collection ([#463](https://github.com/Sparxx947/romseerr/issues/463)) ([7d2bdc8](https://github.com/Sparxx947/romseerr/commit/7d2bdc8125f24f1641c00e66b72a4fe3497acd37)), closes [#462](https://github.com/Sparxx947/romseerr/issues/462)
* **library:** check the whole tree, not two levels ([#469](https://github.com/Sparxx947/romseerr/issues/469)) ([3ae5f97](https://github.com/Sparxx947/romseerr/commit/3ae5f977d9dd35d7910e238f629549795fbec9be)), closes [#465](https://github.com/Sparxx947/romseerr/issues/465)
* **library:** never deduplicate a file an image list names ([#468](https://github.com/Sparxx947/romseerr/issues/468)) ([97b16da](https://github.com/Sparxx947/romseerr/commit/97b16da852078ed295e0830a2a56d2b4f28e1254)), closes [#467](https://github.com/Sparxx947/romseerr/issues/467)
* **library:** separate 'not an archive' from 'damaged archive' ([#473](https://github.com/Sparxx947/romseerr/issues/473)) ([800b195](https://github.com/Sparxx947/romseerr/commit/800b19582ea930c776a98e5885a645324f451908)), closes [#449](https://github.com/Sparxx947/romseerr/issues/449)
* **romm:** romm_scan actually triggers a scan, and says so when it cannot ([#520](https://github.com/Sparxx947/romseerr/issues/520)) ([#524](https://github.com/Sparxx947/romseerr/issues/524)) ([215ccf6](https://github.com/Sparxx947/romseerr/commit/215ccf612d4ff14c1577b42b0f48b322a9a159b6))
* **search:** let a category tenant reclaim its platform from the title ([#453](https://github.com/Sparxx947/romseerr/issues/453)) ([513f0ab](https://github.com/Sparxx947/romseerr/commit/513f0abd1ad44a2f08eaebffbf3678ac26679984)), closes [#452](https://github.com/Sparxx947/romseerr/issues/452)
* **stream:** a missing agent now refuses instead of starting a stale copy ([#500](https://github.com/Sparxx947/romseerr/issues/500)) ([#504](https://github.com/Sparxx947/romseerr/issues/504)) ([7ea78d2](https://github.com/Sparxx947/romseerr/commit/7ea78d2170de08ca53cad988f85cf7cd15714ec8))
* **stream:** a PS3 title died over a probe file it could not write ([#539](https://github.com/Sparxx947/romseerr/issues/539)) ([#561](https://github.com/Sparxx947/romseerr/issues/561)) ([85e7224](https://github.com/Sparxx947/romseerr/commit/85e722403b7c508bd173327c98c7c1893ca61e5f))
* **stream:** a staged PUP is not installed firmware ([#480](https://github.com/Sparxx947/romseerr/issues/480)) ([c26906d](https://github.com/Sparxx947/romseerr/commit/c26906d2ed87a6e3c6eb3657e7c5c4122a2b59ad)), closes [#479](https://github.com/Sparxx947/romseerr/issues/479)
* **stream:** a Vita title is launched by its title id, not its path ([#487](https://github.com/Sparxx947/romseerr/issues/487)) ([dfd7e3f](https://github.com/Sparxx947/romseerr/commit/dfd7e3f7dfe1749dd71e91a5b8080db58becf17e))
* **stream:** an emulator update no longer deletes the emulator ([#441](https://github.com/Sparxx947/romseerr/issues/441)) ([6f210e5](https://github.com/Sparxx947/romseerr/commit/6f210e5760bbc9646611e6531cb689f208e46e87))
* **stream:** Cemu asked an unsupported backend for an audio device and ran mute ([#541](https://github.com/Sparxx947/romseerr/issues/541)) ([#556](https://github.com/Sparxx947/romseerr/issues/556)) ([3bc7372](https://github.com/Sparxx947/romseerr/commit/3bc73729781cee77e8adb717a71c9deef10482a9))
* **stream:** desktop launchers set APPDIR and APPIMAGE ([#483](https://github.com/Sparxx947/romseerr/issues/483)) ([e321312](https://github.com/Sparxx947/romseerr/commit/e32131285817b7184e2920cca960276d85f98d68)), closes [#482](https://github.com/Sparxx947/romseerr/issues/482)
* **stream:** die Flächenmessung vergleicht mit einem Grundbild des leeren Desktops ([#495](https://github.com/Sparxx947/romseerr/issues/495)) ([#497](https://github.com/Sparxx947/romseerr/issues/497)) ([5397620](https://github.com/Sparxx947/romseerr/commit/53976208a913c5c97a6db011980d891610eb31c7))
* **stream:** drei modale Fenster fangen jeden PSX-Start ab — und das Profil lief nie ([#494](https://github.com/Sparxx947/romseerr/issues/494)) ([8788b7f](https://github.com/Sparxx947/romseerr/commit/8788b7fe0df12cf9c69669cdedcba669a81bb0c6))
* **stream:** Eden's player 1 is on the keyboard, not on a pad ([#298](https://github.com/Sparxx947/romseerr/issues/298)) ([#534](https://github.com/Sparxx947/romseerr/issues/534)) ([308119b](https://github.com/Sparxx947/romseerr/commit/308119b838fe35a333bc079cd61902217969b048))
* **stream:** gamepad node order is a race on reconnect, so every emulator bound a silent device ([#535](https://github.com/Sparxx947/romseerr/issues/535)) ([#536](https://github.com/Sparxx947/romseerr/issues/536)) ([7570861](https://github.com/Sparxx947/romseerr/commit/7570861d750ff65d56b7a1b79a3e017a74f2e0cc))
* **stream:** nicht der Fensterschritt holt DuckStation aus dem Vollbild, sondern das F11 danach ([#496](https://github.com/Sparxx947/romseerr/issues/496)) ([0e36cf4](https://github.com/Sparxx947/romseerr/commit/0e36cf479a74efc49d06bfad9ee92f4e541a2a20))
* **stream:** resolve a Wii U title to its .rpx, and refuse an update by name ([#502](https://github.com/Sparxx947/romseerr/issues/502)) ([#511](https://github.com/Sparxx947/romseerr/issues/511)) ([573e02c](https://github.com/Sparxx947/romseerr/commit/573e02cc6c1e007d91a3e359e570d8087e467d4a))
* **stream:** Romseerr refuses a Wii U update too, and a reason without a text is caught ([#512](https://github.com/Sparxx947/romseerr/issues/512), [#513](https://github.com/Sparxx947/romseerr/issues/513)) ([#514](https://github.com/Sparxx947/romseerr/issues/514)) ([76849ab](https://github.com/Sparxx947/romseerr/commit/76849ab0ff9d3ec9d841fb07034b154f9c951329))
* **stream:** stop the emulator, not the wrapper that started it ([#491](https://github.com/Sparxx947/romseerr/issues/491)) ([5e2a2c4](https://github.com/Sparxx947/romseerr/commit/5e2a2c46fbcbafbbf4a6c935bb593162fcccff78)), closes [#489](https://github.com/Sparxx947/romseerr/issues/489)
* **stream:** the load recording listed its own measurement at 100 % ([#529](https://github.com/Sparxx947/romseerr/issues/529)) ([#530](https://github.com/Sparxx947/romseerr/issues/530)) ([14caa7b](https://github.com/Sparxx947/romseerr/commit/14caa7b217d4df3ed709f97b5052069fac2edd5d))
* **stream:** the ownership healing skipped /config/.cache, which is what blocked Cemu ([#509](https://github.com/Sparxx947/romseerr/issues/509)) ([#510](https://github.com/Sparxx947/romseerr/issues/510)) ([0ca0115](https://github.com/Sparxx947/romseerr/commit/0ca01155885aa01c8038b0f050680e7221feb5e6))
* **stream:** the recorded process list said nothing about where it was taken ([#531](https://github.com/Sparxx947/romseerr/issues/531)) ([#532](https://github.com/Sparxx947/romseerr/issues/532)) ([d7e436a](https://github.com/Sparxx947/romseerr/commit/d7e436aab5ea4cec8809ce556af10da97b5ac416))
* **stream:** the stream search ran a second walk and drifted from the index ([#477](https://github.com/Sparxx947/romseerr/issues/477)) ([#499](https://github.com/Sparxx947/romseerr/issues/499)) ([fce6fd6](https://github.com/Sparxx947/romseerr/commit/fce6fd6c898e046a43195b99a6a0f036f84f9547))
* **stream:** the Vita firmware has two parts, and the status must see both ([#485](https://github.com/Sparxx947/romseerr/issues/485)) ([ff56525](https://github.com/Sparxx947/romseerr/commit/ff565256d1c5128b6c1e2485da1de8ae87a0da4b)), closes [#484](https://github.com/Sparxx947/romseerr/issues/484)
* **stream:** the Wii Remote was bound to the mouse pointer, so Wii titles got no input ([#297](https://github.com/Sparxx947/romseerr/issues/297)) ([#559](https://github.com/Sparxx947/romseerr/issues/559)) ([2f704c4](https://github.com/Sparxx947/romseerr/commit/2f704c406197ca4f1e9296c6d8bae585ec119926))
* **stream:** Vita3K is started at the binary, not through its shell wrapper ([#489](https://github.com/Sparxx947/romseerr/issues/489)) ([#508](https://github.com/Sparxx947/romseerr/issues/508)) ([9480727](https://github.com/Sparxx947/romseerr/commit/9480727a859f77974fbf14ff0690cbfa2245a87f))
* **stream:** xemu could not start — the borrowed library was never on the loader's path ([#525](https://github.com/Sparxx947/romseerr/issues/525)) ([#526](https://github.com/Sparxx947/romseerr/issues/526)) ([0351795](https://github.com/Sparxx947/romseerr/commit/0351795b84e7b3f182c6f3e3fbca943c82912130))
* **stream:** xemu's picture was cropped because VirtualGL never followed the resize ([#498](https://github.com/Sparxx947/romseerr/issues/498)) ([#553](https://github.com/Sparxx947/romseerr/issues/553)) ([827e30b](https://github.com/Sparxx947/romseerr/commit/827e30bd12ea3779284cdd81e6d670430f2c5512))
* **stream:** zwei modale Fenster fangen jeden Vita-Start ab ([#490](https://github.com/Sparxx947/romseerr/issues/490)) ([64cbaf9](https://github.com/Sparxx947/romseerr/commit/64cbaf9b6548fc5859d0995897a96586e969cab0)), closes [#488](https://github.com/Sparxx947/romseerr/issues/488)
* **ui:** bind the requests click to the container, not to each row ([#450](https://github.com/Sparxx947/romseerr/issues/450)) ([739e001](https://github.com/Sparxx947/romseerr/commit/739e0014595b7fa952e91cb6c7cb523ab5d71d87))
* **ui:** keep a request click's answer alive across a refresh, and never fail silently ([#460](https://github.com/Sparxx947/romseerr/issues/460)) ([abfae3b](https://github.com/Sparxx947/romseerr/commit/abfae3b2a5fd32c40d8f1f9f1c2a5ddd70c733d1))


### Dokumentation / Documentation

* **library:** write down how a run log makes deletions recoverable ([#476](https://github.com/Sparxx947/romseerr/issues/476)) ([c2c7096](https://github.com/Sparxx947/romseerr/commit/c2c7096bc1711b856dbca7ff41831554584a112a)), closes [#475](https://github.com/Sparxx947/romseerr/issues/475)
* stop offering :latest as the install, it predates every release ([#445](https://github.com/Sparxx947/romseerr/issues/445)) ([7676d46](https://github.com/Sparxx947/romseerr/commit/7676d46998675323172eed408241da3b99141edc))
* **stream:** correct my own claim - Vita3K fetches the font package too ([#486](https://github.com/Sparxx947/romseerr/issues/486)) ([1bdded9](https://github.com/Sparxx947/romseerr/commit/1bdded930f956496cda5a60e5d438e626a35b634)), closes [#484](https://github.com/Sparxx947/romseerr/issues/484)
* write down the release step without which nothing merges ([#451](https://github.com/Sparxx947/romseerr/issues/451)) ([1f604f0](https://github.com/Sparxx947/romseerr/commit/1f604f0fdb95a9359ec5126d2280cac2a73e44bd))

## [1.2.0-beta.1](https://github.com/Sparxx947/romseerr/compare/v1.1.0-beta.1...v1.2.0-beta.1) (2026-08-12)


### Neu / Features

* bring the library reorganiser into the repository ([#349](https://github.com/Sparxx947/romseerr/issues/349)) ([c1ec921](https://github.com/Sparxx947/romseerr/commit/c1ec921ed792c780cb6c52f33bb612e237077e1f))
* **discover:** mark owned and requested titles on the cover, and name the platform ([#225](https://github.com/Sparxx947/romseerr/issues/225)) ([59032d7](https://github.com/Sparxx947/romseerr/commit/59032d7636263103346bd8c36458e59e716cd496)), closes [#205](https://github.com/Sparxx947/romseerr/issues/205)
* **download:** Archive.org S3 keys make restricted items reachable ([#385](https://github.com/Sparxx947/romseerr/issues/385)) ([778afd8](https://github.com/Sparxx947/romseerr/commit/778afd80ac1e7d10c43d93361b1ef0f5e97183e8)), closes [#384](https://github.com/Sparxx947/romseerr/issues/384)
* **downloads:** route Romseerr's own downloads through a proxy, fail-closed ([#348](https://github.com/Sparxx947/romseerr/issues/348)) ([79b31eb](https://github.com/Sparxx947/romseerr/commit/79b31ebdc82d60c1f5a9d343cc0cc1d855369323))
* **import:** bulk import from a watched drop folder ([#414](https://github.com/Sparxx947/romseerr/issues/414)) ([275f87b](https://github.com/Sparxx947/romseerr/commit/275f87bdd12f6bd0bdca303d2a7941d17f138218)), closes [#396](https://github.com/Sparxx947/romseerr/issues/396)
* **jdownloader:** probe the hand-off instead of confirming only our own half ([#253](https://github.com/Sparxx947/romseerr/issues/253)) ([e53a2e3](https://github.com/Sparxx947/romseerr/commit/e53a2e37dd0f0b3455030839dfb7ac7f508c5f10)), closes [#218](https://github.com/Sparxx947/romseerr/issues/218)
* **jobs:** abort work that is alive but no longer progressing ([#347](https://github.com/Sparxx947/romseerr/issues/347)) ([b29b972](https://github.com/Sparxx947/romseerr/commit/b29b972eb1d98e7fbd72ae3c055e7382536616b1))
* **jobs:** delete finished requests individually or by group ([#249](https://github.com/Sparxx947/romseerr/issues/249)) ([06fc68a](https://github.com/Sparxx947/romseerr/commit/06fc68a8c184be81042c0294cf28786d57e46753)), closes [#246](https://github.com/Sparxx947/romseerr/issues/246)
* **jobs:** re-import a kept download instead of fetching it again ([#248](https://github.com/Sparxx947/romseerr/issues/248)) ([60b0fe1](https://github.com/Sparxx947/romseerr/commit/60b0fe1b582a81b5b6f6c10fb9427171107239bb)), closes [#245](https://github.com/Sparxx947/romseerr/issues/245)
* **library-tools:** collect ancillary files off the game level ([#404](https://github.com/Sparxx947/romseerr/issues/404)) ([d291c2a](https://github.com/Sparxx947/romseerr/commit/d291c2a4a88bc64a2fe9436fb6e0e39cb059060f)), closes [#399](https://github.com/Sparxx947/romseerr/issues/399)
* **library-tools:** let context place what an extension cannot ([#409](https://github.com/Sparxx947/romseerr/issues/409)) ([63cf535](https://github.com/Sparxx947/romseerr/commit/63cf53590a25d00497be553809a75386b923249c)), closes [#366](https://github.com/Sparxx947/romseerr/issues/366)
* **library-tools:** name extensionless PRG files by their load address ([#413](https://github.com/Sparxx947/romseerr/issues/413)) ([d5c4d58](https://github.com/Sparxx947/romseerr/commit/d5c4d585946c96f80b456ae112212b2b2bc70d90)), closes [#412](https://github.com/Sparxx947/romseerr/issues/412)
* **library:** give the library a real vendor taxonomy, and filter recommendations ([#335](https://github.com/Sparxx947/romseerr/issues/335)) ([21afbcc](https://github.com/Sparxx947/romseerr/commit/21afbcc6ced489d62ffea90ea0c2ba7c3365314d))
* **maintenance:** show, clear and expire downloads left by failed imports ([#247](https://github.com/Sparxx947/romseerr/issues/247)) ([6cecd23](https://github.com/Sparxx947/romseerr/commit/6cecd23951afc7c4ba34b3cad1ad78f8aa4a0048)), closes [#244](https://github.com/Sparxx947/romseerr/issues/244)
* **platforms:** add SG-1000, drop a core the player does not ship, and check the rest ([#262](https://github.com/Sparxx947/romseerr/issues/262)) ([64ba34c](https://github.com/Sparxx947/romseerr/commit/64ba34cf5cacb95dee02a00f666c64eeb15825f9)), closes [#124](https://github.com/Sparxx947/romseerr/issues/124)
* **release:** create a branch per release, and say how to run an older version ([#187](https://github.com/Sparxx947/romseerr/issues/187)) ([f463fde](https://github.com/Sparxx947/romseerr/commit/f463fde563702ff02a3d62dffbd5472b74eb3889)), closes [#186](https://github.com/Sparxx947/romseerr/issues/186)
* **requests:** count retries and switch source instead of repeating one ([#250](https://github.com/Sparxx947/romseerr/issues/250)) ([1726812](https://github.com/Sparxx947/romseerr/commit/1726812b4d580bfb851101178f4d3a8c7832c4cd)), closes [#200](https://github.com/Sparxx947/romseerr/issues/200)
* **requests:** filter by state with counts, and a badge for unfinished jobs ([#230](https://github.com/Sparxx947/romseerr/issues/230)) ([618b626](https://github.com/Sparxx947/romseerr/commit/618b626892c71ead64d2bcd6754f2f67cddc9397))
* **settings:** section menu on top, one page per notification method and connection ([#223](https://github.com/Sparxx947/romseerr/issues/223)) ([645861b](https://github.com/Sparxx947/romseerr/commit/645861b0cf41b9978ab5a13eb84fa0dac3ce4871)), closes [#202](https://github.com/Sparxx947/romseerr/issues/202)
* **stream:** add an optional second seat as its own container ([#281](https://github.com/Sparxx947/romseerr/issues/281)) ([179612a](https://github.com/Sparxx947/romseerr/commit/179612abb894bdedd90a3d80cdf0648d5aa10480)), closes [#137](https://github.com/Sparxx947/romseerr/issues/137)
* **stream:** add DuckStation so PlayStation 1 can be streamed as well ([#270](https://github.com/Sparxx947/romseerr/issues/270)) ([52cdb6a](https://github.com/Sparxx947/romseerr/commit/52cdb6ae6dd6d7621bab71e59cb4cf41c63e22b2)), closes [#268](https://github.com/Sparxx947/romseerr/issues/268)
* **stream:** allow more than one session at a time ([#280](https://github.com/Sparxx947/romseerr/issues/280)) ([c157034](https://github.com/Sparxx947/romseerr/commit/c157034a93e2606c785fc501b4a301a0603f42e1)), closes [#137](https://github.com/Sparxx947/romseerr/issues/137)
* **stream:** bind the gamepad in Azahar, and record how 3DS becomes playable ([#304](https://github.com/Sparxx947/romseerr/issues/304), [#299](https://github.com/Sparxx947/romseerr/issues/299)) ([#308](https://github.com/Sparxx947/romseerr/issues/308)) ([3d180b5](https://github.com/Sparxx947/romseerr/commit/3d180b5184cf4304f2422c26531ce7b290360414))
* **stream:** bind xemu player one to the bridged pad ([#433](https://github.com/Sparxx947/romseerr/issues/433)) ([da7b8cc](https://github.com/Sparxx947/romseerr/commit/da7b8cc515bae4d8f6b745d8f1b1a4d8bdbe87f4))
* **stream:** classify the uncovered platforms and close the cheapest gap ([#193](https://github.com/Sparxx947/romseerr/issues/193)) ([#292](https://github.com/Sparxx947/romseerr/issues/292)) ([aa23892](https://github.com/Sparxx947/romseerr/commit/aa2389241f528f1b9f99178eb958544d70ac197d))
* **stream:** decrypt 3DS titles on demand into a cache ([#355](https://github.com/Sparxx947/romseerr/issues/355)) ([4b9e137](https://github.com/Sparxx947/romseerr/commit/4b9e1373f77fa7290229b223f73990e6007d9dcc)), closes [#354](https://github.com/Sparxx947/romseerr/issues/354)
* **stream:** deliver gamepads to the emulators as real kernel devices ([#265](https://github.com/Sparxx947/romseerr/issues/265)) ([1cb0840](https://github.com/Sparxx947/romseerr/commit/1cb084075b4b9da358df92b4a1503d3b7c26e70a)), closes [#119](https://github.com/Sparxx947/romseerr/issues/119)
* **stream:** install .cia titles instead of refusing them ([#365](https://github.com/Sparxx947/romseerr/issues/365)) ([36b451c](https://github.com/Sparxx947/romseerr/commit/36b451c25ce01311d856911f97ff129de7704ee8)), closes [#315](https://github.com/Sparxx947/romseerr/issues/315)
* **stream:** map the GameCube pad to the bridged controller at launch ([#267](https://github.com/Sparxx947/romseerr/issues/267)) ([d9194e0](https://github.com/Sparxx947/romseerr/commit/d9194e06173b22434b53499859f563b2d8aa982f)), closes [#119](https://github.com/Sparxx947/romseerr/issues/119)
* **stream:** reject encrypted 3DS titles before launching ([#299](https://github.com/Sparxx947/romseerr/issues/299)) ([#307](https://github.com/Sparxx947/romseerr/issues/307)) ([ffaad2e](https://github.com/Sparxx947/romseerr/commit/ffaad2e0f29a8e2e337aa1f138fd0dc708684b7b))
* **stream:** update emulators one at a time, and keep three builds to roll back to ([#342](https://github.com/Sparxx947/romseerr/issues/342)) ([c74cf62](https://github.com/Sparxx947/romseerr/commit/c74cf626ed4342529a8f04d95aa657417ebb6c2b))
* **ui:** a request row leads to the game's card ([#407](https://github.com/Sparxx947/romseerr/issues/407)) ([90ccb6c](https://github.com/Sparxx947/romseerr/commit/90ccb6c01e42722c21b12b9a852b229dbc87cb98)), closes [#390](https://github.com/Sparxx947/romseerr/issues/390)
* **ui:** browse the titles we already own, by manufacturer and system ([#293](https://github.com/Sparxx947/romseerr/issues/293)) ([#294](https://github.com/Sparxx947/romseerr/issues/294)) ([a91b9e4](https://github.com/Sparxx947/romseerr/commit/a91b9e466c0c83f6a581769118e0d4323e9fdc5c))
* **ui:** give every view an address so the browser can navigate ([#222](https://github.com/Sparxx947/romseerr/issues/222)) ([81fa6d8](https://github.com/Sparxx947/romseerr/commit/81fa6d8b9511fe3be9831ff6fd57ca30d8994d45)), closes [#194](https://github.com/Sparxx947/romseerr/issues/194)
* **ui:** give the drop folder a panel instead of API-only access ([#417](https://github.com/Sparxx947/romseerr/issues/417)) ([ea5f7ca](https://github.com/Sparxx947/romseerr/commit/ea5f7ca23a4acbdbc5ed74d2226c1cf5079235e4))
* **ui:** group coverage by manufacturer, and read logos from the operator's folder ([#231](https://github.com/Sparxx947/romseerr/issues/231)) ([ee8cdee](https://github.com/Sparxx947/romseerr/commit/ee8cdeecbf58f2b6efab8f5d3362ecb8e4183b61)), closes [#199](https://github.com/Sparxx947/romseerr/issues/199) [#211](https://github.com/Sparxx947/romseerr/issues/211)
* **ui:** make the second seat configurable and show how many are free ([#282](https://github.com/Sparxx947/romseerr/issues/282)) ([5063ff5](https://github.com/Sparxx947/romseerr/commit/5063ff58cefc8a4221c4fd9039d76be68dddcc8d)), closes [#137](https://github.com/Sparxx947/romseerr/issues/137)
* **ui:** move language and user area to the top right, behind menus ([#224](https://github.com/Sparxx947/romseerr/issues/224)) ([a8106b0](https://github.com/Sparxx947/romseerr/commit/a8106b061886a93499a08356d31bd4268223e218)), closes [#206](https://github.com/Sparxx947/romseerr/issues/206)
* **ui:** move the wishlist out of requests and add a favourites list beside it ([#229](https://github.com/Sparxx947/romseerr/issues/229)) ([313b13a](https://github.com/Sparxx947/romseerr/commit/313b13a6d2bd415c97583fcfa2f3a7a03535beb3)), closes [#195](https://github.com/Sparxx947/romseerr/issues/195) [#207](https://github.com/Sparxx947/romseerr/issues/207)
* **ui:** pin a footer with the running version, and let Escape close the detail dialog ([#227](https://github.com/Sparxx947/romseerr/issues/227)) ([fa6cd8a](https://github.com/Sparxx947/romseerr/commit/fa6cd8aefe2016381b778ec5ff5849771ab13056)), closes [#208](https://github.com/Sparxx947/romseerr/issues/208) [#226](https://github.com/Sparxx947/romseerr/issues/226)
* **ui:** ratings and comments per title, and a blocklist that explains itself ([#232](https://github.com/Sparxx947/romseerr/issues/232)) ([324c44b](https://github.com/Sparxx947/romseerr/commit/324c44bb02e51d2c53766725b63ea2d76cbb6365)), closes [#203](https://github.com/Sparxx947/romseerr/issues/203) [#210](https://github.com/Sparxx947/romseerr/issues/210)
* **usenet:** measure the usenet path stage by stage without downloading ([#233](https://github.com/Sparxx947/romseerr/issues/233)) ([51f2b18](https://github.com/Sparxx947/romseerr/commit/51f2b184fe7bfd81ec93e9f6d00f11356bb623a7)), closes [#196](https://github.com/Sparxx947/romseerr/issues/196)


### Behoben / Fixes

* **ci:** build the release image from release-please, not from an event that cannot fire ([#261](https://github.com/Sparxx947/romseerr/issues/261)) ([727c010](https://github.com/Sparxx947/romseerr/commit/727c0105548d8419803faa157c84f92aba116d75)), closes [#185](https://github.com/Sparxx947/romseerr/issues/185)
* **ci:** Scorecard only runs on the default branch — drop the push trigger ([#370](https://github.com/Sparxx947/romseerr/issues/370)) ([5e2e817](https://github.com/Sparxx947/romseerr/commit/5e2e81791e9e9786da83365f0b03eadb89542e20)), closes [#369](https://github.com/Sparxx947/romseerr/issues/369)
* **compose:** host paths and the app share variable names — two silent breakages ([#377](https://github.com/Sparxx947/romseerr/issues/377)) ([#401](https://github.com/Sparxx947/romseerr/issues/401)) ([3d8c3f2](https://github.com/Sparxx947/romseerr/commit/3d8c3f2d8a2d7837f4d9a98cd0169dd976aae4ae))
* **download:** name the reason a download failed, and mark restricted items first ([#383](https://github.com/Sparxx947/romseerr/issues/383)) ([73cf08e](https://github.com/Sparxx947/romseerr/commit/73cf08e57f002c296f21bf0b9b2fbb3cf9c7e1f6)), closes [#382](https://github.com/Sparxx947/romseerr/issues/382)
* **import:** 16 home-computer formats were unknown ([#411](https://github.com/Sparxx947/romseerr/issues/411)) ([9d1ea0c](https://github.com/Sparxx947/romseerr/commit/9d1ea0c3dc4d1d207486ff06eebdb70aa2ed7d1b)), closes [#410](https://github.com/Sparxx947/romseerr/issues/410)
* **import:** an arrived title counts as imported, and inherits library permissions ([#415](https://github.com/Sparxx947/romseerr/issues/415)) ([7d27ea3](https://github.com/Sparxx947/romseerr/commit/7d27ea38806bbd9c5bec4ad07602c57cc30b7095)), closes [#396](https://github.com/Sparxx947/romseerr/issues/396)
* **import:** move a game directory as one title instead of scattering its files ([#408](https://github.com/Sparxx947/romseerr/issues/408)) ([bb65262](https://github.com/Sparxx947/romseerr/commit/bb652626993330381d2f1ea50709f43686ee62f4)), closes [#391](https://github.com/Sparxx947/romseerr/issues/391)
* **import:** survive client-renamed files and stop deleting failed downloads ([#243](https://github.com/Sparxx947/romseerr/issues/243)) ([81ddc8a](https://github.com/Sparxx947/romseerr/commit/81ddc8a4a5fa68a3d16bd6fbca8fa467e58eaa77)), closes [#240](https://github.com/Sparxx947/romseerr/issues/240) [#241](https://github.com/Sparxx947/romseerr/issues/241) [#242](https://github.com/Sparxx947/romseerr/issues/242)
* **import:** Wii U, PS Vita and Xbox had no importable extension at all ([#392](https://github.com/Sparxx947/romseerr/issues/392)) ([7b163b3](https://github.com/Sparxx947/romseerr/commit/7b163b378d0ed49c73a6a6d233c536a1ce9e6510)), closes [#391](https://github.com/Sparxx947/romseerr/issues/391)
* **jdownloader:** derive the output view from the downloader view and surface a broken hand-off ([#213](https://github.com/Sparxx947/romseerr/issues/213)) ([22f2d64](https://github.com/Sparxx947/romseerr/commit/22f2d646b9ef196fba90befd00bf8ec338aa4039)), closes [#197](https://github.com/Sparxx947/romseerr/issues/197) [#204](https://github.com/Sparxx947/romseerr/issues/204)
* **jdownloader:** write the .crawljob field types JDownloader can actually parse ([#220](https://github.com/Sparxx947/romseerr/issues/220)) ([00b27b3](https://github.com/Sparxx947/romseerr/commit/00b27b325ef6b75277444ca2fadc60df2aa61352)), closes [#219](https://github.com/Sparxx947/romseerr/issues/219)
* **jobs:** clear in-flight jobs after a restart instead of leaving them stuck ([#339](https://github.com/Sparxx947/romseerr/issues/339)) ([46d5405](https://github.com/Sparxx947/romseerr/commit/46d54052a978490eeea2f07123b2c2f1bfeba993))
* **library-tools:** a platform that crashed was recorded as done ([#397](https://github.com/Sparxx947/romseerr/issues/397)) ([#398](https://github.com/Sparxx947/romseerr/issues/398)) ([b5d36e2](https://github.com/Sparxx947/romseerr/commit/b5d36e23e3c7f2f6ca2e18561f8008d2c10ddb1b))
* **library-tools:** do not empty a platform whose games look like ancillary files ([#405](https://github.com/Sparxx947/romseerr/issues/405)) ([d0853a2](https://github.com/Sparxx947/romseerr/commit/d0853a2cc765a5ef97262ca3343437882b8b9965)), closes [#399](https://github.com/Sparxx947/romseerr/issues/399)
* **library-tools:** name the file when a rebuild step fails ([#426](https://github.com/Sparxx947/romseerr/issues/426)) ([97bfe71](https://github.com/Sparxx947/romseerr/commit/97bfe71dc1f4ecd560a0831ac7d19146b3975f25))
* **library-tools:** resume an aborted --alle run instead of starting over ([#372](https://github.com/Sparxx947/romseerr/issues/372)) ([ab3dc24](https://github.com/Sparxx947/romseerr/commit/ab3dc242a30b807ec33c2c12ff34d4cecee34ebe)), closes [#371](https://github.com/Sparxx947/romseerr/issues/371)
* **library:** a platform that cannot be read is named, not silently counted as empty ([#400](https://github.com/Sparxx947/romseerr/issues/400)) ([6de645d](https://github.com/Sparxx947/romseerr/commit/6de645da2f28827b68566c389c7770d7fcefa07b)), closes [#381](https://github.com/Sparxx947/romseerr/issues/381)
* **library:** stop inventing a platform called "Mixed" ([#368](https://github.com/Sparxx947/romseerr/issues/368)) ([3ce5eb0](https://github.com/Sparxx947/romseerr/commit/3ce5eb0191ee08a0294c76b28a0b0172f8abac27)), closes [#367](https://github.com/Sparxx947/romseerr/issues/367)
* **requests:** read user names from the list the API actually returns ([#215](https://github.com/Sparxx947/romseerr/issues/215)) ([80a854b](https://github.com/Sparxx947/romseerr/commit/80a854bc17e2c6067d4d1f39d5e53e97bd5389f8)), closes [#209](https://github.com/Sparxx947/romseerr/issues/209)
* **search:** ask every source, and rank confirmed matches first ([#376](https://github.com/Sparxx947/romseerr/issues/376)) ([48490ec](https://github.com/Sparxx947/romseerr/commit/48490ec9c10ccd0e292fbf2e4c010fe8ffdb40fa)), closes [#375](https://github.com/Sparxx947/romseerr/issues/375)
* **search:** platform detection missed the most common spellings ([#394](https://github.com/Sparxx947/romseerr/issues/394)) ([7a501db](https://github.com/Sparxx947/romseerr/commit/7a501dbfc452a3d3b0d4be5417b7afc3daa0872c)), closes [#393](https://github.com/Sparxx947/romseerr/issues/393)
* **security:** tighten key permissions at startup, not only when a key is read ([#257](https://github.com/Sparxx947/romseerr/issues/257)) ([dfeba98](https://github.com/Sparxx947/romseerr/commit/dfeba98f043281644fedeb8348e9e4eb50cba117)), closes [#256](https://github.com/Sparxx947/romseerr/issues/256)
* **startup:** report a read-only /config instead of running as if nothing were wrong ([#217](https://github.com/Sparxx947/romseerr/issues/217)) ([ac7a7c0](https://github.com/Sparxx947/romseerr/commit/ac7a7c0a2df671be0bc055a4cefef6a4bfe42c87)), closes [#216](https://github.com/Sparxx947/romseerr/issues/216)
* **stream:** 3DS decryption never installed — wrong filename, wrong precondition ([#357](https://github.com/Sparxx947/romseerr/issues/357)) ([5b12f02](https://github.com/Sparxx947/romseerr/commit/5b12f02ce6fd61906a14df9e8154f7fbe49c740a)), closes [#356](https://github.com/Sparxx947/romseerr/issues/356)
* **stream:** decide 3DS format by content, not by file extension ([#423](https://github.com/Sparxx947/romseerr/issues/423)) ([6fef30e](https://github.com/Sparxx947/romseerr/commit/6fef30e56de7ee2717eb5f14025bf6ed3fd817c7))
* **stream:** DuckStation does not know PCSX2's Face* names ([#275](https://github.com/Sparxx947/romseerr/issues/275)) ([da752c9](https://github.com/Sparxx947/romseerr/commit/da752c964a832e3ff658e64d85e6a87bffab8db6)), closes [#268](https://github.com/Sparxx947/romseerr/issues/268)
* **stream:** DuckStation names the face buttons A/B/X/Y, read from its source ([#277](https://github.com/Sparxx947/romseerr/issues/277)) ([99203b2](https://github.com/Sparxx947/romseerr/commit/99203b29b13ab95a0429ef0c935693822bb5ec42)), closes [#268](https://github.com/Sparxx947/romseerr/issues/268)
* **stream:** DuckStation resets the setup wizard flag, so check the value ([#274](https://github.com/Sparxx947/romseerr/issues/274)) ([2d43fa7](https://github.com/Sparxx947/romseerr/commit/2d43fa79b596ce02e639e9e29563550f26f2a4e8)), closes [#268](https://github.com/Sparxx947/romseerr/issues/268)
* **stream:** find the decrypted CIA instead of recomputing its name ([#389](https://github.com/Sparxx947/romseerr/issues/389)) ([088febe](https://github.com/Sparxx947/romseerr/commit/088febe41db6d088f484b1a51330ddb0d2b7df92)), closes [#388](https://github.com/Sparxx947/romseerr/issues/388)
* **stream:** let the title ID decide alone which file is the base game ([#174](https://github.com/Sparxx947/romseerr/issues/174)) ([#291](https://github.com/Sparxx947/romseerr/issues/291)) ([536a205](https://github.com/Sparxx947/romseerr/commit/536a205be094faf2a06f82cc25a891ec78c32797))
* **stream:** make xemu start and produce sound ([#300](https://github.com/Sparxx947/romseerr/issues/300)) ([#305](https://github.com/Sparxx947/romseerr/issues/305)) ([f5200dd](https://github.com/Sparxx947/romseerr/commit/f5200dd493e54201eb77108589f7e6c621a76984))
* **stream:** measure the painted area and correct, instead of assuming fullscreen ([#430](https://github.com/Sparxx947/romseerr/issues/430)) ([22ff6f7](https://github.com/Sparxx947/romseerr/commit/22ff6f71d510eb7dcf457ad328e0da1de6c1d363))
* **stream:** pick the base game, not its update ([#287](https://github.com/Sparxx947/romseerr/issues/287)) ([61d9e38](https://github.com/Sparxx947/romseerr/commit/61d9e383c113d3842657df7eee6c08ad9c2c782c)), closes [#174](https://github.com/Sparxx947/romseerr/issues/174)
* **stream:** point RPCS3 at the name SDL actually reports, and ship the mapping ([#271](https://github.com/Sparxx947/romseerr/issues/271)) ([bbf8da2](https://github.com/Sparxx947/romseerr/commit/bbf8da2c9f7fbee68932c118d40d731315e21320)), closes [#119](https://github.com/Sparxx947/romseerr/issues/119)
* **stream:** reap the emulator after kill instead of leaving a zombie ([#432](https://github.com/Sparxx947/romseerr/issues/432)) ([9eac115](https://github.com/Sparxx947/romseerr/commit/9eac115ecb5161ba72e1fce7f2d74df3f214fe0c))
* **stream:** refuse an unplayable 3DS title before a seat is taken ([#353](https://github.com/Sparxx947/romseerr/issues/353)) ([5c0b230](https://github.com/Sparxx947/romseerr/commit/5c0b230e955c518302c144579890203859eee03f))
* **stream:** refuse Switch updates and DLC before a seat is taken ([#431](https://github.com/Sparxx947/romseerr/issues/431)) ([e76bdea](https://github.com/Sparxx947/romseerr/commit/e76bdea5fe852bc3352dbbd48354780379ba9ad3))
* **stream:** remove gamepad nodes on shutdown, and fix a race in the probe ([#266](https://github.com/Sparxx947/romseerr/issues/266)) ([400660c](https://github.com/Sparxx947/romseerr/commit/400660ce1660d48ffd7661bfe78eb2b9e0a1f296)), closes [#119](https://github.com/Sparxx947/romseerr/issues/119)
* **stream:** report a permission error instead of throwing it ([#286](https://github.com/Sparxx947/romseerr/issues/286)) ([a3ef154](https://github.com/Sparxx947/romseerr/commit/a3ef154546969ab1d55acb73a7778c8c98b4432f)), closes [#273](https://github.com/Sparxx947/romseerr/issues/273)
* **stream:** report the error dialog instead of a silent empty stream ([#288](https://github.com/Sparxx947/romseerr/issues/288)) ([#290](https://github.com/Sparxx947/romseerr/issues/290)) ([c4f6625](https://github.com/Sparxx947/romseerr/commit/c4f6625fff1d62564c1856c4891de3c473b6345c))
* **stream:** run the launch service as abc, not root ([#279](https://github.com/Sparxx947/romseerr/issues/279)) ([bb51873](https://github.com/Sparxx947/romseerr/commit/bb51873684e14af0d0653e34598d3e0bf37af34a)), closes [#273](https://github.com/Sparxx947/romseerr/issues/273)
* **stream:** send the byte Selkies waits for, or no event ever arrives ([#269](https://github.com/Sparxx947/romseerr/issues/269)) ([2e9ec8a](https://github.com/Sparxx947/romseerr/commit/2e9ec8a077efe5f442cc9aaafc2c852ff80e7054)), closes [#119](https://github.com/Sparxx947/romseerr/issues/119)
* **stream:** turn GPU encoding back on with SELKIES_AUTO_GPU ([#285](https://github.com/Sparxx947/romseerr/issues/285)) ([148dfd0](https://github.com/Sparxx947/romseerr/commit/148dfd0fb13b05d05cd7d27075e674ce194ef19e)), closes [#283](https://github.com/Sparxx947/romseerr/issues/283)
* **stream:** xemu runs — picture, sound and gamepad confirmed ([#300](https://github.com/Sparxx947/romseerr/issues/300)) ([#306](https://github.com/Sparxx947/romseerr/issues/306)) ([d3f0321](https://github.com/Sparxx947/romseerr/commit/d3f03212e2e6f3fea671f1009ee6faa1462a304b))
* **ui:** make the library view keyboard-operable and stop indexing hidden folders ([#333](https://github.com/Sparxx947/romseerr/issues/333)) ([68c6bbd](https://github.com/Sparxx947/romseerr/commit/68c6bbdd9287f16f61db0faa36df8fb8bdc4b5cf))
* **ui:** make the sidebar keyboard-reachable and give the library a route ([#332](https://github.com/Sparxx947/romseerr/issues/332)) ([897ee39](https://github.com/Sparxx947/romseerr/commit/897ee394591d2fc33a8999478ed9f4c460b72714))
* **ui:** offer the platforms instead of a dead end when a title is ambiguous ([#252](https://github.com/Sparxx947/romseerr/issues/252)) ([2aa648e](https://github.com/Sparxx947/romseerr/commit/2aa648e010eba2955ffaaf4008c06d834126fca9)), closes [#175](https://github.com/Sparxx947/romseerr/issues/175)
* **ui:** one source for the sidebar icons, and complete the translations ([#341](https://github.com/Sparxx947/romseerr/issues/341)) ([a2dc009](https://github.com/Sparxx947/romseerr/commit/a2dc0099205156989a745ee34ff7c8b13dc0825d))
* **ui:** read the RetroAchievements status instead of hardcoding it grey ([#387](https://github.com/Sparxx947/romseerr/issues/387)) ([600e7ab](https://github.com/Sparxx947/romseerr/commit/600e7ab09c414be13449aa4c40798bffd2e94713)), closes [#386](https://github.com/Sparxx947/romseerr/issues/386)
* **ui:** trap focus in the detail dialog and return it on close ([#259](https://github.com/Sparxx947/romseerr/issues/259)) ([a0bebb3](https://github.com/Sparxx947/romseerr/commit/a0bebb3adf06307cca4d0e0c4706f5031cc9a92d)), closes [#258](https://github.com/Sparxx947/romseerr/issues/258)
* **usenet:** fail jobs SABnzbd gave up on, and verify indexers serve NZBs ([#237](https://github.com/Sparxx947/romseerr/issues/237)) ([51cdb49](https://github.com/Sparxx947/romseerr/commit/51cdb494d4066ed6e986e856dfbaf07b55f69d09)), closes [#235](https://github.com/Sparxx947/romseerr/issues/235) [#236](https://github.com/Sparxx947/romseerr/issues/236)
* **usenet:** read the field names search_usenet actually returns ([#239](https://github.com/Sparxx947/romseerr/issues/239)) ([6dc0452](https://github.com/Sparxx947/romseerr/commit/6dc0452ba0130e59355bbfb72647b6354947c664)), closes [#238](https://github.com/Sparxx947/romseerr/issues/238)
* **users:** enforce the last-admin invariant in save_users, not just on import ([#251](https://github.com/Sparxx947/romseerr/issues/251)) ([1747041](https://github.com/Sparxx947/romseerr/commit/1747041fd71e9a6a5cdad1ca9ff3fd1dac27f1ba)), closes [#234](https://github.com/Sparxx947/romseerr/issues/234)
* **web:** serve .json assets with a real content type, and compress them ([#352](https://github.com/Sparxx947/romseerr/issues/352)) ([d670739](https://github.com/Sparxx947/romseerr/commit/d670739ed75e9f494de8abe01efe4e89813654da))


### Leistung / Performance

* **web:** pre-compress assets, and document 401 in the spec ([#334](https://github.com/Sparxx947/romseerr/issues/334)) ([194a2b3](https://github.com/Sparxx947/romseerr/commit/194a2b389d8d613c7d0ac1517c474a4a6b42b866))


### Dokumentation / Documentation

* audit every file for documentation gaps and guard the findings ([#418](https://github.com/Sparxx947/romseerr/issues/418)) ([92aec4a](https://github.com/Sparxx947/romseerr/commit/92aec4a9def211e96d3d7c49d8cc62dfcaf88f8d))
* **ci:** note that .gitleaks.toml must exist in every scanned tree ([#363](https://github.com/Sparxx947/romseerr/issues/363)) ([cee16db](https://github.com/Sparxx947/romseerr/commit/cee16dbad740de572d7f40c4a6fdcc67300b1e37)), closes [#358](https://github.com/Sparxx947/romseerr/issues/358)
* cover the drop folder in docs/ and repair two rendering faults ([#421](https://github.com/Sparxx947/romseerr/issues/421)) ([7c30a9b](https://github.com/Sparxx947/romseerr/commit/7c30a9b7f457fd136ea3e32d0105b502ce364cc3))
* **jdownloader:** correct the measurement behind the crawljob fix, and name the real blocker ([#221](https://github.com/Sparxx947/romseerr/issues/221)) ([3df32c1](https://github.com/Sparxx947/romseerr/commit/3df32c1d2e202d5a11c526a3f6be6e26769dc282)), closes [#219](https://github.com/Sparxx947/romseerr/issues/219)
* **readme:** the English README had no way back from a bad update ([#378](https://github.com/Sparxx947/romseerr/issues/378)) ([#402](https://github.com/Sparxx947/romseerr/issues/402)) ([83b776d](https://github.com/Sparxx947/romseerr/commit/83b776d52bbe6ac7af77406e66f2876345eb1fc9))
* **stream:** 3DS is playable — update the compatibility table ([#360](https://github.com/Sparxx947/romseerr/issues/360)) ([e2ae48e](https://github.com/Sparxx947/romseerr/commit/e2ae48e71c74e6cabd9c44f1becf394538283a82)), closes [#359](https://github.com/Sparxx947/romseerr/issues/359)
* **stream:** document token rotation, and tell a mismatch apart from an outage ([#260](https://github.com/Sparxx947/romseerr/issues/260)) ([edaadab](https://github.com/Sparxx947/romseerr/commit/edaadab052c89973e77a3794517e21154797b3ec)), closes [#177](https://github.com/Sparxx947/romseerr/issues/177)
* **stream:** measure fullscreen at the pixels, not at the window geometry ([#374](https://github.com/Sparxx947/romseerr/issues/374)) ([23bb4cf](https://github.com/Sparxx947/romseerr/commit/23bb4cf631bde15a7ae5294e8ac3f7d7b50f8a8b)), closes [#316](https://github.com/Sparxx947/romseerr/issues/316)
* **stream:** on Unraid the template is the truth, not the running container ([#373](https://github.com/Sparxx947/romseerr/issues/373)) ([f34be07](https://github.com/Sparxx947/romseerr/commit/f34be07b651bd1246ea260550e2eaa324b9132ef)), closes [#317](https://github.com/Sparxx947/romseerr/issues/317)
* **stream:** record what has actually been tested per emulator ([#136](https://github.com/Sparxx947/romseerr/issues/136)) ([#289](https://github.com/Sparxx947/romseerr/issues/289)) ([3c9e5c0](https://github.com/Sparxx947/romseerr/commit/3c9e5c0fced85f39d16b71254a09c0114e972ee7))
* **stream:** record why certbot stays a sidecar ([#191](https://github.com/Sparxx947/romseerr/issues/191)) ([#296](https://github.com/Sparxx947/romseerr/issues/296)) ([464c358](https://github.com/Sparxx947/romseerr/commit/464c35827918725f71587599f2b5551c0c4cc62b))
* **stream:** the DRI3 switch works now, VirtualGL is no longer used ([#169](https://github.com/Sparxx947/romseerr/issues/169)) ([#295](https://github.com/Sparxx947/romseerr/issues/295)) ([b9504ac](https://github.com/Sparxx947/romseerr/commit/b9504ac76da78883c883528cdbab633c92a30544))
* **stream:** what two simultaneous sessions actually cost, measured ([#284](https://github.com/Sparxx947/romseerr/issues/284)) ([1a27355](https://github.com/Sparxx947/romseerr/commit/1a2735584b6dec35f677aba5a03d1c93f12c5944)), closes [#137](https://github.com/Sparxx947/romseerr/issues/137)


### Umbau / Refactoring

* **i18n:** move four of five language tables out of index.js ([#351](https://github.com/Sparxx947/romseerr/issues/351)) ([ad512c9](https://github.com/Sparxx947/romseerr/commit/ad512c9f27978b32c53fc0a58fadaa8c3a129b67))

## [1.1.0-beta.1](https://github.com/Sparxx947/romseerr/compare/v1.0.0-beta.1...v1.1.0-beta.1) (2026-08-08)


### Neu / Features

* add configuration export and import ([#85](https://github.com/Sparxx947/romseerr/issues/85)) ([d82256f](https://github.com/Sparxx947/romseerr/commit/d82256f2ea2d91a389616eb703033ca4280aabf4))
* add in-browser play via RomM's built-in EmulatorJS player ([#93](https://github.com/Sparxx947/romseerr/issues/93)) ([f381d3c](https://github.com/Sparxx947/romseerr/commit/f381d3cc51a5f42728634e9b181e2e9ade0769c1))
* add the home computers and early consoles the player can actually run ([#144](https://github.com/Sparxx947/romseerr/issues/144)) ([cd9b68e](https://github.com/Sparxx947/romseerr/commit/cd9b68e0c8c66a4e456f00db749af7b37654f10f))
* expose operational metrics at /metrics ([#82](https://github.com/Sparxx947/romseerr/issues/82)) ([e59df94](https://github.com/Sparxx947/romseerr/commit/e59df948c6ee6d50c96fe49213ca4a2fbb51ba6e))
* expose running version via /api/version ([#81](https://github.com/Sparxx947/romseerr/issues/81)) ([fce767d](https://github.com/Sparxx947/romseerr/commit/fce767da5988a5754da33d8f3d15177895dafcde))
* import a wishlist from a pasted list or file ([#84](https://github.com/Sparxx947/romseerr/issues/84)) ([a3218fc](https://github.com/Sparxx947/romseerr/commit/a3218fc8905c955cbb51bb5d16f6afe9ee33c21d))
* install emulators on demand from Romseerr, not automatically ([#110](https://github.com/Sparxx947/romseerr/issues/110)) ([abf85ef](https://github.com/Sparxx947/romseerr/commit/abf85ef8dabb35d38086e75f8ddb6b6405eb380a))
* JDownloader service status and configurable paths ([#91](https://github.com/Sparxx947/romseerr/issues/91)) ([d423bc9](https://github.com/Sparxx947/romseerr/commit/d423bc9faed7ba9e05f79505fc85f8b62e6c6ebc))
* let an instance say whether it knows what it is running ([#143](https://github.com/Sparxx947/romseerr/issues/143)) ([da4cb18](https://github.com/Sparxx947/romseerr/commit/da4cb1893f190f50038cc0ad9eddc135e893e3c9))
* more emulators, and update/rollback from Romseerr ([#103](https://github.com/Sparxx947/romseerr/issues/103)) ([b73d221](https://github.com/Sparxx947/romseerr/commit/b73d221449f914672f1fa587bfdc1cdd3a3b656e))
* per-platform coverage and a browsable missing-titles list ([#86](https://github.com/Sparxx947/romseerr/issues/86)) ([22b15c7](https://github.com/Sparxx947/romseerr/commit/22b15c7118a2a4209ea969d47e625ce12dcf62ef))
* resolve platform folder names instead of renaming the library ([#138](https://github.com/Sparxx947/romseerr/issues/138)) ([cd910b0](https://github.com/Sparxx947/romseerr/commit/cd910b09c66eba7f1e063234a6403498181833bd))
* ship the streaming host in this repository ([#98](https://github.com/Sparxx947/romseerr/issues/98)) ([5fea21b](https://github.com/Sparxx947/romseerr/commit/5fea21b6f930f6dbf32108d2c5d262688c894e21))
* show RetroAchievements data on the detail view ([#87](https://github.com/Sparxx947/romseerr/issues/87)) ([b56c7bd](https://github.com/Sparxx947/romseerr/commit/b56c7bdeb1dcc6101c7e837cd9e5e1248ed6de7a))
* stream natively-emulated platforms into the browser ([#96](https://github.com/Sparxx947/romseerr/issues/96)) ([f6b81ec](https://github.com/Sparxx947/romseerr/commit/f6b81ec337aa141c290559410dec8aa846c86264))
* **stream:** add a gamepad check page, because the stream page eats F12 ([#134](https://github.com/Sparxx947/romseerr/issues/134)) ([0124ec8](https://github.com/Sparxx947/romseerr/commit/0124ec899181b582650f3af6b67b1264b57931b8))
* **stream:** add a setup starter, and give the pad name its index ([#161](https://github.com/Sparxx947/romseerr/issues/161)) ([7ee37ad](https://github.com/Sparxx947/romseerr/commit/7ee37ad98cd371bbbe2624666b9d66ed1e8ca1b4)), closes [#160](https://github.com/Sparxx947/romseerr/issues/160)
* **stream:** bind the controller automatically before each launch ([#132](https://github.com/Sparxx947/romseerr/issues/132)) ([8ad0972](https://github.com/Sparxx947/romseerr/commit/8ad0972a065028ee1b7f9aa0db02966e1474cb77))
* **stream:** make PS3 reachable — resolve RPCS3, and launch folder titles ([#147](https://github.com/Sparxx947/romseerr/issues/147)) ([9902ca4](https://github.com/Sparxx947/romseerr/commit/9902ca4e5a600a0cdbee9fdcd945213f7225a2e8))
* **stream:** manage BIOS and firmware without obtaining any ([#120](https://github.com/Sparxx947/romseerr/issues/120)) ([ce2251f](https://github.com/Sparxx947/romseerr/commit/ce2251fd78600920583f23c3fe8ecf0bc048137c))
* **stream:** pick the BIOS that matches the title's region ([#140](https://github.com/Sparxx947/romseerr/issues/140)) ([bdc75cf](https://github.com/Sparxx947/romseerr/commit/bdc75cfbab361ab5fc930191f780e67096f1fa61))
* **stream:** show only the emulator, not the desktop around it ([#145](https://github.com/Sparxx947/romseerr/issues/145)) ([40327a1](https://github.com/Sparxx947/romseerr/commit/40327a197faa3d6a5b74f458e76d1b6945b79f36))
* un-stub the filehoster path with a generic catalogue-JSON indexer ([#92](https://github.com/Sparxx947/romseerr/issues/92)) ([68c6c02](https://github.com/Sparxx947/romseerr/commit/68c6c024cead443c7666ded299ac2316019d964f))


### Behoben / Fixes

* **ci:** keep release tags continuous, drop the component prefix ([#115](https://github.com/Sparxx947/romseerr/issues/115)) ([0ee985a](https://github.com/Sparxx947/romseerr/commit/0ee985adc1e9984bed72f319684fa6a02946f497))
* **ci:** let release-please carry the version into the OpenAPI spec ([#182](https://github.com/Sparxx947/romseerr/issues/182)) ([6c4de40](https://github.com/Sparxx947/romseerr/commit/6c4de40357efcf0e5b4df54972a14d5331f445ea)), closes [#181](https://github.com/Sparxx947/romseerr/issues/181)
* **ci:** let the release commit hold the release version ([#184](https://github.com/Sparxx947/romseerr/issues/184)) ([806fc5c](https://github.com/Sparxx947/romseerr/commit/806fc5c835424e4e4165d145e0b551f16a539c81)), closes [#183](https://github.com/Sparxx947/romseerr/issues/183)
* **firmware:** match by size where the file names legitimately vary ([#173](https://github.com/Sparxx947/romseerr/issues/173)) ([583c65d](https://github.com/Sparxx947/romseerr/commit/583c65d0790c52e31c511ade8d0a0aef412e9946)), closes [#172](https://github.com/Sparxx947/romseerr/issues/172)
* **library:** strip PS3 disc IDs and the ps3 platform tag in norm() ([#153](https://github.com/Sparxx947/romseerr/issues/153)) ([3f50c57](https://github.com/Sparxx947/romseerr/commit/3f50c579eb37514dfc0980a8f0a45649ca7b6b8e)), closes [#152](https://github.com/Sparxx947/romseerr/issues/152)
* mount the launch agent instead of expecting it in /config ([#105](https://github.com/Sparxx947/romseerr/issues/105)) ([ec77799](https://github.com/Sparxx947/romseerr/commit/ec77799f4c0db06bfd8cf39b52cc77c310df9e53))
* pass the init scripts' variables into the container ([#99](https://github.com/Sparxx947/romseerr/issues/99)) ([326b305](https://github.com/Sparxx947/romseerr/commit/326b3056aa936a4ac67c1ad73e43fc8cff27d1b0))
* refuse outbound requests to internal targets and stop leaking exception text ([#94](https://github.com/Sparxx947/romseerr/issues/94)) ([82fd45e](https://github.com/Sparxx947/romseerr/commit/82fd45e1e27a1385f5f714de08b6c986c98248d3))
* stop returning exception text from import, TLS upload and catalogue status ([#95](https://github.com/Sparxx947/romseerr/issues/95)) ([1d7e3fa](https://github.com/Sparxx947/romseerr/commit/1d7e3fada235f8ca453ad5c25f9c5335db568515))
* **stream:** bind RPCS3 player one to SDL instead of the keyboard ([#157](https://github.com/Sparxx947/romseerr/issues/157)) ([c385f24](https://github.com/Sparxx947/romseerr/commit/c385f24fd7c73a7260925ef0b156bf9e2d34d4b7)), closes [#156](https://github.com/Sparxx947/romseerr/issues/156)
* **stream:** count a folder title as present in the library ([#151](https://github.com/Sparxx947/romseerr/issues/151)) ([20a596f](https://github.com/Sparxx947/romseerr/commit/20a596f8ca69bb0893d24443e4556efdf0b50abf)), closes [#150](https://github.com/Sparxx947/romseerr/issues/150)
* **stream:** do not abort on an unset LD_PRELOAD, and add ShellCheck ([#126](https://github.com/Sparxx947/romseerr/issues/126)) ([fe2b483](https://github.com/Sparxx947/romseerr/commit/fe2b483cc012edebc9aa1fba7daa5adc7d499eac))
* **stream:** give emulators the gamepad variable Selkies documents ([#125](https://github.com/Sparxx947/romseerr/issues/125)) ([8ae9bf5](https://github.com/Sparxx947/romseerr/commit/8ae9bf5b8160e06dce13b387c4326182c22ed594))
* **stream:** keep Vita firmware in one place, not two ([#121](https://github.com/Sparxx947/romseerr/issues/121)) ([fd8ef66](https://github.com/Sparxx947/romseerr/commit/fd8ef66720061368996a03862b47af4ce4bbead1))
* **stream:** let the emulator read its own firmware, and place before reporting ([#122](https://github.com/Sparxx947/romseerr/issues/122)) ([e33794d](https://github.com/Sparxx947/romseerr/commit/e33794d41080c41f6834a27c4e66bcb196514aea))
* **stream:** never overwrite an RPCS3 mapping, and stop claiming the pad is ready ([#159](https://github.com/Sparxx947/romseerr/issues/159)) ([3644b10](https://github.com/Sparxx947/romseerr/commit/3644b10a1f03cec4586cae7d26e68277fdee87fa)), closes [#158](https://github.com/Sparxx947/romseerr/issues/158)
* **stream:** own the firmware parent directory, not just what is inside it ([#123](https://github.com/Sparxx947/romseerr/issues/123)) ([9cb8d09](https://github.com/Sparxx947/romseerr/commit/9cb8d09917f5ca4e4bce87278b386ea9441a6e54))
* **stream:** pin the display backend instead of relying on Wayland being absent ([#179](https://github.com/Sparxx947/romseerr/issues/179)) ([17693e7](https://github.com/Sparxx947/romseerr/commit/17693e72de3ec4d976f6d1b15d16a1b7063e30cf)), closes [#178](https://github.com/Sparxx947/romseerr/issues/178)
* **stream:** report firmware the emulator has, not the file it was made from ([#163](https://github.com/Sparxx947/romseerr/issues/163)) ([0b6f49d](https://github.com/Sparxx947/romseerr/commit/0b6f49d71140f1def2f602902bb688f7a76b4271)), closes [#162](https://github.com/Sparxx947/romseerr/issues/162)
* **stream:** send a library-relative path, and say why a launch failed ([#131](https://github.com/Sparxx947/romseerr/issues/131)) ([9a1e72b](https://github.com/Sparxx947/romseerr/commit/9a1e72bb9dcc2d061ebd587bf72d030d33b920d5))
* **stream:** ship Dolphin as an AppImage; the apt build never opens a window ([#166](https://github.com/Sparxx947/romseerr/issues/166)) ([8f06866](https://github.com/Sparxx947/romseerr/commit/8f06866da549cd6c3982b030acb73286ac30507d)), closes [#165](https://github.com/Sparxx947/romseerr/issues/165)
* **stream:** stop mounting into the web root the image wipes on boot ([#146](https://github.com/Sparxx947/romseerr/issues/146)) ([02c7f1e](https://github.com/Sparxx947/romseerr/commit/02c7f1e256339189275e6122be9e45becd7e3128))
* **stream:** take LD_PRELOAD from the image, do not rebuild it by hand ([#128](https://github.com/Sparxx947/romseerr/issues/128)) ([4b2f2ec](https://github.com/Sparxx947/romseerr/commit/4b2f2ece6233c42869f00701b701375f2ae2f1d2))
* **stream:** take the platform from the library, not from the search hit ([#155](https://github.com/Sparxx947/romseerr/issues/155)) ([5fcefce](https://github.com/Sparxx947/romseerr/commit/5fcefce31a4fff9d04ff7d002a5f25fca8ca9fb3)), closes [#154](https://github.com/Sparxx947/romseerr/issues/154)
* **stream:** two emulators installed into one shared directory ([#180](https://github.com/Sparxx947/romseerr/issues/180)) ([b8a6ed6](https://github.com/Sparxx947/romseerr/commit/b8a6ed63f9d5d76ac2dd488d5a6993e65810538a)), closes [#176](https://github.com/Sparxx947/romseerr/issues/176)


### Dokumentation / Documentation

* state the content policy, and enforce it in CI ([#109](https://github.com/Sparxx947/romseerr/issues/109)) ([e50be1e](https://github.com/Sparxx947/romseerr/commit/e50be1eb176c8ca2b488cd6e22eba11ab48a446c))


### Umbau / Refactoring

* move the front-end out of Python strings into templates/ and static/ ([#90](https://github.com/Sparxx947/romseerr/issues/90)) ([8cd9d41](https://github.com/Sparxx947/romseerr/commit/8cd9d41eb53c7522c6849010ed13979e9568cf7d))

## [Unreleased]

### Hinzugefügt / Added
- **Anfrage im Namen eines anderen Nutzers** — Admins (Recht `manage_requests`) können in der
  Detailansicht einen Empfänger wählen; die Anfrage läuft dann auf dessen Konto (auto-freigegeben,
  Push an den Empfänger). / **Request on behalf of another user** — admins can pick a recipient in the detail view.
- **Weitere Melde-Agenten** — **Gotify**, **ntfy** und **Pushover** nativ in den Benachrichtigungen
  (zusätzlich zu Discord/Telegram/Webhook/E-Mail/Push). / **More notification agents** — native Gotify, ntfy and Pushover.
- **Download-Fortschritt** — laufende Usenet-Downloads zeigen jetzt den Prozentsatz aus der
  SABnzbd-Warteschlange im Anfragen-Status (statt nur „Lädt…"). /
  **Download progress** — active Usenet downloads show the SABnzbd percentage in the request status.
- **Multi-Arch-Image (amd64 + arm64)** — der Release-Workflow baut das Image jetzt für beide
  Architekturen (läuft damit auch auf Raspberry Pi & Co.). /
  **Multi-arch image (amd64 + arm64)** — the release workflow now builds for both architectures.
- **Private Nachrichten zwischen Benutzern** — neuer Bereich „✉ Nachrichten": Direktnachrichten
  an andere Nutzer mit Verlauf je Gesprächspartner, **Ungelesen-Zähler** (Badge in der Sidebar)
  und „als gelesen"-Markierung. Empfänger wird optional über Web-Push + persönlichen Webhook
  benachrichtigt. SQLite-Tabelle `messages`; `GET/POST /api/messages`, `POST /api/messages/read`. /
  **Private messages between users** — a "Messages" section with per-partner threads, an unread
  badge and read receipts; recipients optionally notified via web push + personal webhook.
- **Erststart-Assistent** — beim ersten Start (Admin, noch nicht „onboarded") führt ein Wizard
  Schritt für Schritt durch die Verbindungen (SABnzbd/Prowlarr/IGDB/RomM) mit Test je Schritt;
  jederzeit über Einstellungen → Über erneut aufrufbar. Flag `onboarded` in den Einstellungen. /
  **First-run wizard** — guides new admins through the stack connections step by step with a
  per-step test; reopenable from Settings → About.
- **Ausführlicher „Über"-Bereich** — Version, Bibliotheks-/Anfragen-Statistik, Links (Repo, Wiki,
  API-Doku, Changelog, Issues, Security), Funktions- und Stack-Überblick, Lizenz. /
  **Detailed "About" section** — version, library/request stats, links, feature & stack overview.

### Geändert / Changed
- **Rebrand-Aufräumen** — restliche `rom-suche`/`romsuche_`-Verweise im Code durch `Romseerr`/
  `romseerr_` ersetzt (Log „Romseerr startet…", Logdatei `romseerr.log`, Job-/Ordnernamen
  `romseerr_<id>`, JD-Pfade). Gemeinsprachliches „ROM-Suche" bleibt. /
  **Rebrand cleanup** — remaining `rom-suche`/`romsuche_` references replaced with `Romseerr`/
  `romseerr_` (log line, log file, job/folder names, JD paths).

### Hinzugefügt / Added
- **HTTPS-Zertifikat über die Weboberfläche** — Admin kann unter Einstellungen → **HTTPS** ein
  TLS-Zertifikat + Schlüssel (PEM) hinterlegen (validiert, `/config/tls`, 600). Ist es aktiviert,
  startet die App zusätzlich einen **HTTPS-Listener** auf einem eigenen Port (Default **8443**);
  HTTP auf 8770 bleibt. Ermöglicht Web-Push/PWA ohne separaten Reverse-Proxy. Status zeigt
  CN/Ablauf; der private Schlüssel wird nie ausgegeben. `GET/POST /api/settings/tls`,
  `POST /api/settings/tls/remove`. /
  **HTTPS certificate via the web UI** — admins can upload a TLS cert+key (PEM) under Settings →
  HTTPS; when enabled the app also serves HTTPS on a separate port (default 8443). Status shows
  CN/expiry; the private key is never returned.
- **Scraper-Quellen + Klartext-Anzeige in „Verbindungen"** — neue Felder für **SteamGridDB**
  (Key, als **Cover-Fallback** verdrahtet, wenn IGDB kein Cover hat) und **ScreenScraper**
  (User/Passwort). Secret-Felder haben jetzt einen **👁-Umschalter**, um den Wert im **Klartext**
  anzuzeigen (Admin, via `GET /api/settings/connections/reveal`). SteamGridDB erscheint im
  Dienste-Status/Test. /
  **Scraper sources + reveal in "Connections"** — SteamGridDB (key, wired as a cover fallback)
  and ScreenScraper (user/password); secret fields get a 👁 toggle to show the value in clear
  text (admin, via `/api/settings/connections/reveal`).
- **Dienst-Verbindungen über die Einstellungsseite** — SABnzbd/Prowlarr/IGDB/RomM/JDownloader
  (URLs, API-Keys, Kategorien, Pfade) sind jetzt im Admin-Bereich unter **„Verbindungen"**
  editierbar, mit **`.env` als Fallback** (leeres Feld = Env-Wert). Secrets werden maskiert und
  nur bei Neueingabe überschrieben; „Test"-Knopf prüft die Erreichbarkeit. Werte werden zur
  Laufzeit über `cfg()` gelesen. Die Secrets liegen nur in der Laufzeit-DB unter `/config`
  (gitignoriert), nie im Repo. /
  **Service connections editable in Settings** — SABnzbd/Prowlarr/IGDB/RomM/JDownloader are now
  configurable in the admin "Connections" section, with `.env` as fallback (empty = env value);
  secrets are masked and only overwritten on new input; a test button checks reachability.
- **Default-Avatar** — Nutzer ohne Profilbild bekommen jetzt einen erzeugten Avatar
  (Initiale auf farbigem Kreis) in Sidebar und Profil statt eines leeren Kreises. /
  **Default avatar** — users without a picture get a generated initials avatar.
- **Fehlgeschlagene/abgelehnte Anfragen erneut versuchen** — Knopf „↻ Erneut" in den Anfragen
  (Recht `manage_requests`); `POST /api/jobs/{id}/retry` reiht den Job wieder ein. /
  **Retry failed/denied requests** — "↻ Retry" button; `POST /api/jobs/{id}/retry`.
- **Konfig-Check beim Start** — warnt im Log, wenn IGDB/SABnzbd/Prowlarr fehlen oder nicht
  erreichbar sind (nicht fatal, im Hintergrund). /
  **Startup config check** — logs a warning when IGDB/SABnzbd/Prowlarr are missing or unreachable.

### Geändert / Changed
- **Alle Stores in SQLite** — die letzten JSON-Stores (**settings, issues, maillog, push_subs**)
  liegen jetzt in einem `kv`-Table in `romseerr.db`; bestehende JSON werden beim Start
  verlustfrei migriert (danach `.migrated`). Nur `secret.key`/`vapid.json` bleiben Dateien
  (Secrets). Damit ist die gesamte Persistenz in der Datenbank. /
  **All stores in SQLite** — the remaining JSON stores (settings, issues, maillog, push_subs)
  now live in a `kv` table in `romseerr.db`, migrated losslessly on startup; only the key
  files stay on disk.

### Sicherheit / Security
- **Login-Bruteforce-Schutz** — max. 8 Fehlversuche je (IP, Benutzer) in 5 min, danach HTTP 429.
- **Cookie-Härtung** — Session-Cookie `HttpOnly` + `SameSite=Strict` (CSRF-Schutz); `Secure`
  automatisch, wenn `ROMSEERR_HTTPS=1` (hinter TLS-Proxy).
- **Container läuft als non-root** — Dockerfile `USER 1000` (echter Fix des Trivy-Funds
  AVD-DS-0002 statt Unterdrückung); Volumes müssen dem Laufzeit-User gehören (z. B. `--user 99:100`).
  Zusätzlich `HEALTHCHECK` im Image. /
  **Login brute-force protection** (429 after 8 fails), **hardened session cookie**
  (HttpOnly + SameSite=Strict, Secure via `ROMSEERR_HTTPS=1`), **non-root container**
  (`USER 1000`, real fix for AVD-DS-0002) and an image `HEALTHCHECK`.

### Dokumentation / Documentation
- **Ausführliche Code-Kommentierung** — Modul-Docstring (Architektur, Datenhaltung, Auth,
  Fallstricke), Docstrings auf den nicht-trivialen Funktionen (Index, Worker, Import, Auth,
  Push) und erklärte Abschnitts-Header in `app.py`; `docs/ARCHITECTURE.md` um einen
  **Code-Rundgang** erweitert (Dateiaufbau, Anfrage-Lebenszyklus, „neue Route hinzufügen",
  Fallstricke). /
  **Extensive code documentation** — module docstring, docstrings on the non-trivial functions,
  and a code tour in `docs/ARCHITECTURE.md`.

### Behoben / Fixed
- **CI grün** — `match` als Variablenname (Ruff hielt das Soft-Keyword für ein `match`-Statement)
  → in `matched` umbenannt; bewusste `0.0.0.0`-Bindung mit `# nosec B104` markiert (Bandit);
  Trivy-Action auf gültige Version `0.35.0` gepinnt (0.24.0 existierte nicht mehr); CodeQL auf
  privaten Repos übersprungen statt rot. /
  **Green CI** — renamed `match` variable (tripped Ruff), annotated the intentional `0.0.0.0`
  bind with `# nosec B104`, pinned Trivy to a valid version, skip CodeQL on private repos.
- **Startseite lud keine Spiele / Admin-Menü tot** — in `loadLogs()` stand `join('\n')`
  im **nicht-rohen** Python-`PAGE`-String; Python wandelte `\n` in einen echten Zeilenumbruch
  um, sodass das ausgelieferte Inline-JavaScript ein **unterminiertes String-Literal** enthielt
  und das gesamte Skript nicht lief (keine Discover-Spiele, kein funktionierendes Admin-Portal).
  Gefixt zu `join('\\n')`. **Lehre:** JS-Escapes im `PAGE`-String immer verdoppeln — Syntaxprüfung
  muss gegen den **interpretierten** String laufen (über den Python-AST), nicht gegen den Quelltext. /
  **Home page loaded no games / admin menu dead** — `loadLogs()` used `join('\n')` inside the
  non-raw Python `PAGE` string; Python turned `\n` into a real newline, so the served inline
  JavaScript had an **unterminated string literal** and the whole script failed. Fixed to `join('\\n')`.

### Hinzugefügt / Added
- **Beitragenden-Infrastruktur** — `CONTRIBUTING.md` (zweisprachig), `SECURITY.md`
  (private Sicherheitsmeldung aktiviert), `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1),
  Issue-Formulare (Bug/Feature) + PR-Vorlage, sowie **Dependency-Review** auf PRs
  (blockiert neue Abhängigkeiten mit HIGH-Schwachstellen). /
  **Contributor infrastructure** — bilingual `CONTRIBUTING.md`, `SECURITY.md` (private
  vulnerability reporting enabled), `CODE_OF_CONDUCT.md`, issue forms + PR template, and
  **dependency review** on PRs.

### Hinzugefügt / Added
- **Versioniertes Image nach GHCR** — bei jedem veröffentlichten Release baut ein Workflow
  das Docker-Image und pusht es nach `ghcr.io/sparxx947/romseerr` (Tags `X.Y.Z`, `X.Y`,
  `latest`); so lässt sich ein fertiges Image ziehen statt lokal zu bauen. /
  **Versioned image to GHCR** — on each published release a workflow builds and pushes the
  image to `ghcr.io/sparxx947/romseerr` (tags `X.Y.Z`, `X.Y`, `latest`).

### Hinzugefügt / Added
- **API-Dokumentation (OpenAPI 3.1)** — vollständige, maschinenlesbare Spezifikation als
  einzige Quelle der Wahrheit (`app.OPENAPI`), ausgeliefert unter **`/api/openapi.json`** und
  interaktiv unter **`/api/docs`** (Redoc). Zweisprachige Anleitung in [`docs/API.md`](docs/API.md),
  generierte [`docs/openapi.yaml`](docs/openapi.yaml) (via `scripts/build_openapi.py`). Tests
  erzwingen, dass **jede Route dokumentiert** ist und die Repo-YAML nicht abdriftet. /
  **API documentation (OpenAPI 3.1)** — complete machine-readable spec (single source
  `app.OPENAPI`), served at **`/api/openapi.json`** and rendered at **`/api/docs`** (Redoc);
  bilingual guide in `docs/API.md`, generated `docs/openapi.yaml`. Tests enforce that every
  route is documented and the YAML stays in sync.

### Hinzugefügt / Added
- **Smoke-Tests (pytest) + Inline-JS-Guard** — die CI prüft jetzt **Verhalten**, nicht nur
  Syntax: Health, Titel-Normalisierung/Dedup, Bibliotheks-Index, Sperrliste, Setup/Login,
  Auth-Schutz. Zusätzlich verifiziert ein Test, dass das **eingebettete JavaScript gültig
  parst** (via `node --check` des interpretierten `PAGE`-Strings) — genau die Fehlerklasse,
  die `py_compile` nicht fängt. Neuer CI-Job **Tests**. /
  **Smoke tests (pytest) + inline-JS guard** — CI now checks behavior, not just syntax
  (health, normalization/dedup, index, blocklist, setup/login, auth); plus a test that the
  embedded JavaScript parses (`node --check` on the interpreted `PAGE`). New CI job **Tests**.

### Geändert / Changed
- **Basis-Pfade per Env überschreibbar** — `ROMSEERR_CONFIG` (Default `/config`) und
  `ROMSEERR_ROMS` (Default `/roms`) steuern die Datenverzeichnisse; nötig für Tests, nützlich
  für flexible Deployments. Verhalten mit Defaults unverändert. /
  **Configurable base paths** — `ROMSEERR_CONFIG` / `ROMSEERR_ROMS` (defaults unchanged).
- **users + jobs in SQLite** — Benutzer und Anfragen liegen jetzt in `/config/romseerr.db`
  (Tabellen `users`, `jobs`) statt in JSON-Dateien; bestehende `users.json`/`jobs.json` werden
  beim ersten Start **automatisch übernommen** und als `.migrated` gesichert (verlustfrei, erst
  nach erfolgreichem Commit umbenannt). Funktionssignaturen unverändert. /
  **users + jobs in SQLite** — users and requests now live in `/config/romseerr.db`
  (tables `users`, `jobs`) instead of JSON files; existing `users.json`/`jobs.json` are
  auto-migrated on first start and kept as `.migrated` (lossless, renamed only after commit).

### Hinzugefügt / Added
- **Persistenter Bibliotheks-Index (SQLite)** — der Dedup-Index (~96.000 Titel) wird jetzt in
  `/config/romseerr.db` gespeichert und beim Start **aus der DB geladen** statt jedes Mal aus dem
  Dateisystem aufgebaut: **Startzeit ~24 s → ~1 s**. Im Hintergrund frischt der Index weiter auf
  (Start + alle 10 min); Dedup/`in_library` unverändert. /
  **Persistent library index (SQLite)** — the dedup index (~96k titles) is stored in
  `/config/romseerr.db` and loaded from the DB on startup instead of walking the filesystem
  every time: **startup ~24 s → ~1 s**. Background refresh keeps it current; dedup unchanged.
- **PWA + Web-Push** — Romseerr ist jetzt eine **installierbare PWA** (Manifest, Icon,
  Service-Worker) und kann **Web-Push-Benachrichtigungen** senden, wenn ein ROM verfügbar
  wird. Aktivierung pro Nutzer im Profil (🔔). VAPID-Schlüssel werden beim ersten Start
  erzeugt (`/config/vapid.json`), Abos je Nutzer gespeichert. **Hinweis:** Service-Worker
  und Push funktionieren im Browser nur über **HTTPS** (oder localhost) — hinter einem
  TLS-Reverse-Proxy betreiben. Endpunkte `GET /api/push/pubkey`, `POST /api/push/subscribe`,
  `/api/push/unsubscribe`, `/api/push/test`. Neue Abhängigkeit `pywebpush`. /
  **PWA + web push** — Romseerr is now an **installable PWA** (manifest, icon, service
  worker) and sends **web-push notifications** when a ROM becomes available. Per-user
  opt-in in the profile (🔔). VAPID keys generated on first start; subscriptions stored
  per user. **Note:** service workers and push only work over **HTTPS** (or localhost) —
  run behind a TLS reverse proxy. New dependency `pywebpush`.
- **Mehr Sprachen** — Oberfläche jetzt auch auf **Französisch und Spanisch** (zusätzlich
  zu Deutsch/Englisch); Umschalter in der Sidebar (DE/EN/FR/ES), Profil- und
  Standardsprache-Auswahl erweitert. Alle vier Sprachen vollständig (97 Schlüssel je Sprache). /
  **More languages** — UI now also in **French and Spanish** (besides German/English);
  sidebar switch (DE/EN/FR/ES), profile and default-language selectors extended;
  all four languages complete (97 keys each).
- **Logs & Wartung (Admin)** — neuer Einstellungs-Unterbereich: **Protokollansicht**
  (letzte Log-Zeilen), **Statistik** (Anfragen aktiv/fertig, Bibliotheksgröße, Cache),
  und Wartungsknöpfe **Cache leeren**, **neu indexieren**, **fertige Anfragen entfernen**.
  `GET /api/logs`, `GET /api/admin/stats`, `POST /api/admin/cache/clear`,
  `POST /api/admin/reindex`, `POST /api/jobs/clear-finished`. /
  **Logs & maintenance (admin)** — new settings section: **log view**, **stats**
  (active/finished requests, library size, cache), and maintenance buttons
  **clear cache**, **reindex**, **clear finished requests**.
- **Issue-Kommentare** — Problemmeldungen haben jetzt einen **Kommentar-Verlauf**;
  der Melder und Bearbeiter (Recht `manage_issues`) schreiben Antworten, Staff-Kommentare
  sind markiert (🛠). Fremde ohne Recht werden abgewiesen (403). `POST /api/issues/<id>/comment`. /
  **Issue comments** — issues now have a **comment thread**; the reporter and staff
  (`manage_issues`) can reply, staff comments are marked (🛠); others are refused (403).
- **Detailseite-Tiefe** — die Detailansicht zeigt jetzt **Wertung, Erscheinungsjahr,
  Entwickler und Genres** (Badges), einen **Screenshot-Streifen** und **ähnliche Spiele**
  (anklickbar → neue Suche), alles via IGDB. /
  **Detail depth** — the detail view now shows **rating, release year, developer and
  genres** (badges), a **screenshot strip** and **similar games** (clickable → new search),
  all via IGDB.
- **Discover-Tiefe** — zusätzlich zu „beliebt je Konsole" jetzt **Genre-Reihen** (RPG,
  Jump 'n' Run, Shooter, Racing … via IGDB) und **anpassbares Discover**: Reihen
  ein-/ausblenden (pro Browser gespeichert). /
  **Discover depth** — genre rows (RPG, platform, shooter, racing …) in addition to
  per-console, plus customizable discover (show/hide rows).
- **Anfrage-Kontingente (Quotas)** — Admin setzt X Anfragen pro Y Tage; Nutzer ohne
  „kein Limit"-Recht (`quota_exempt`) werden bei Überschreitung abgelehnt; Rest-Kontingent
  im Profil. /
  **Request quotas** — admins set X requests per Y days; users without the `quota_exempt`
  permission are refused when exceeded; remaining quota shown in the profile.
- **Granulare Berechtigungen** — statt nur admin/user ein Rechte-Set pro Benutzer
  (anfragen, Auto-Freigabe, Anfragen/Benutzer/Probleme/Einstellungen verwalten,
  kontingentfrei); Admins haben implizit alle. Durchgesetzt auf Freigabe/Benutzer/Issues;
  Rechte-Häkchen in der Benutzerverwaltung. /
  **Granular permissions** — per-user permission set instead of just admin/user
  (request, autoapprove, manage requests/users/issues/settings, quota-exempt);
  admins implicitly have all; enforced on approvals/users/issues.
- **Weitere Benachrichtigungs-Agenten** — neben Discord jetzt **Telegram**, **generischer
  Webhook** (Slack/Gotify/Pushover-kompatibel) und **E-Mail bei Verfügbarkeit** (an den
  anfragenden Nutzer). `notify_send` sendet an alle aktiven Agenten. /
  **More notification agents** — besides Discord: Telegram, a generic webhook
  (Slack/Gotify/Pushover-compatible) and email on availability (to the requesting user).
- **API-Key** — programmatischer API-Zugriff ohne Session-Login (Header `X-Api-Key` oder
  `?apikey=`); Key im Admin-Bereich (Allgemein) anzeigen/kopieren/regenerieren.
  `GET /api/apikey`, `POST /api/apikey/regenerate`. /
  **API key** — programmatic API access without a session (header `X-Api-Key` or `?apikey=`);
  view/copy/regenerate in the admin general settings.
- **Probleme/Issues** — Nutzer melden Probleme zu einem ROM (defekt, falsche Region/Plattform,
  sonstiges); Admin sieht alle und schließt/löscht, Nutzer sehen eigene; „Problem melden" auch
  aus der Detailansicht. `/api/issues` (GET/POST), `/api/issues/<id>/close` + DELETE. /
  **Issues** — users report problems about a ROM; admins see/close/delete all, users see their
  own; "report issue" also from the detail view.
- **Mail-Protokoll** — Versand-Log (Zeit, Empfänger, Betreff, Erfolg/Fehler) im Admin-Bereich
  (Benachrichtigungen), persistiert, auf 100 gekappt. `GET /api/maillog`. /
  **Mail log** — send log (time, recipient, subject, success/error) in the admin
  notifications section, persisted, capped at 100.
- **Sperrliste (Blocklist)** — Admin pflegt Stichwörter; passende Titel werden aus Suche
  und Startseite gefiltert und können nicht angefragt werden. `GET/POST /api/blocklist`. /
  **Blocklist** — admins maintain keywords; matching titles are filtered from search and
  the home page and cannot be requested.
- **Passwort-Reset per E-Mail** — SMTP-Konfiguration in den Einstellungen (Host/Port/User/
  Passwort/Absender/TLS + Testmail); „Passwort vergessen?" auf der Login-Seite → zeitlich
  begrenzter Reset-Link (1 h) per Mail; Reset-Seite `/reset`. Endpunkte `/api/forgot`,
  `/api/reset`, `/api/settings/mail-test`. /
  **Password reset via email** — SMTP config in settings (host/port/user/pass/from/TLS +
  test mail); "Forgot password?" on the login page → time-limited reset link (1h) by mail;
  reset page `/reset`.
- **Benutzerprofil** — je Nutzer: Anzeigename, E-Mail, **Avatar-Bild** (Upload → Data-URI),
  Sprache, eigenes Passwort ändern, **persönlicher Discord-Webhook** (bei Verfügbarkeit
  werden allgemeiner **und** persönlicher Webhook benachrichtigt); Avatar in der Sidebar.
  Endpunkte `/api/profile` (GET/POST), `/api/profile/password`, `/api/profile/notify-test`. /
  **User profile** — per user: display name, email, **avatar image** (upload → data URI),
  language, change own password, **personal Discord webhook** (on availability both the
  global and personal webhooks fire); avatar in the sidebar.
- **Admin-Bereich / Settings-Seite** mit Unterbereichen (Allgemein, Benachrichtigungen,
  Benutzer, Dienste-Status, Über); Benutzerverwaltung + Discord dort gebündelt;
  neue Endpunkte `GET /api/services/status`, erweiterte `/api/settings` (general:
  App-Name, Standardsprache), `version` in `/api/auth/status`. /
  **Admin area / settings page** with sections (General, Notifications, Users,
  Services status, About); user management + Discord consolidated there;
  new `GET /api/services/status`, extended `/api/settings` (general: app name,
  default language), `version` in `/api/auth/status`.
- **CI/CD** — GitHub Actions: Lint/Compile/Docker-Build, Security (CodeQL, Bandit, Trivy, gitleaks),
  Release-Bot (release-please), Dependabot; MIT-Lizenz. /
  **CI/CD** — GitHub Actions: lint/compile/docker build, security (CodeQL, Bandit, Trivy, gitleaks),
  release bot (release-please), Dependabot; MIT license.
- **i18n Deutsch + Englisch** — Sprachumschalter (DE/EN) in der Sidebar, Auswahl via `localStorage`;
  Ober­fläche über `data-i18n` und `t()` übersetzt. /
  **i18n German + English** — language switch (DE/EN) in the sidebar, stored in `localStorage`;
  UI translated via `data-i18n` and `t()`.

### Geändert
- **Rebrand zu „Romseerr"** (vormals rom-suche).
- **Seerr-Layout:** feste Sidebar (Entdecken / Anfragen / Benutzer / Abmelden) statt Tab-Leiste.

### Hinzugefügt
- **Einstellungen → Benachrichtigungen:** Discord-Webhook in der Oberfläche konfigurierbar
  (aktiv/URL) mit Test-Knopf; `notify_send` nutzt Einstellungen, fällt auf `DISCORD_WEBHOOK` zurück.
- **Berechtigungen & Freigabe-Workflow:** je Benutzer „Auto-Freigabe"; Anfragen von
  Nutzern ohne Auto-Freigabe landen als **pending** und müssen vom Admin freigegeben
  (oder abgelehnt) werden. Endpunkte `/api/settings`, `/api/users/<u>` (PATCH),
  `/api/jobs/<id>/approve|deny`.
- **Usenet-Cover:** werden lazy über IGDB nachgeladen (`/api/cover`), Release-Titel
  vorher auf den Spielnamen bereinigt.
- **Benutzerverwaltung / Login:** Session-Auth, Ersteinrichtung (Admin anlegen),
  Rollen (admin/user), Admin kann Benutzer anlegen/löschen. Alle Routen geschützt.
  Endpunkte `/api/auth/status`, `/api/login`, `/api/setup`, `/api/logout`, `/api/users`.
- **Startseite mit Konsolen-Reihen:** beliebte Spiele je wichtiger Konsole (IGDB-Popularität),
  sortiert nach Bedeutung; Klick auf ein Poster sucht den Titel plattform-scoped. `GET /api/discover/rows`.
- **Detail-Ansicht** (Modal): Cover, IGDB-Beschreibung, Metadaten, Archive.org-Dateiliste,
  Versionen/Quellen desselben Titels (`gkey`-Gruppierung). `GET /api/detail`.
- **Anfragen-Status** im Seerr-Stil (Angefragt → Lädt → Wird verarbeitet → Verfügbar).
- **Benachrichtigung bei Verfügbarkeit** via Discord-Webhook (`DISCORD_WEBHOOK`, optional).
- Plattform-Vorauswahl in der Suche (Chips, Mehrfachauswahl, `localStorage`).
  Usenet wird breit über *Console* abgefragt und nach Plattform nachgefiltert;
  reine Retro-Auswahl überspringt Usenet. Neuer Endpunkt `GET /api/platforms`.

## [0.1.0] - 2026-08-06

### Hinzugefügt
- Erste Version: Seerr-artige ROM-Suche über Archive.org + Usenet (Prowlarr/SABnzbd).
- Dedup gegen bestehende Bibliothek, Plattform-Erkennung an der Dateiendung.
- Auto-Import (entpacken via `unar`, Einsortierung nach `/roms/<plattform>/`).
- Weboberfläche (:8770), `docker-compose`, Konfiguration über `.env`.
