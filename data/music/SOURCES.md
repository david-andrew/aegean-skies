# Radio note library

These are **note sequences**, not recordings. Audio is made by `src/music_synth.jo`.
No soundtrack recordings, soundfonts, voice models or generated audio assets ship.
`tools/music_pack.py` converts the checked-in source MIDI to compact events; its only
third-party build dependency is `mido`. It has no network access. Runtime needs neither
Python nor MIDI software. The generated `.z` files and `src/music_data.jo` are checked in.
The status of every piece considered for the game, in the catalogue or not, is in `docs/music-status.md`.

## Sources and permissions (checked 12 November 2026)

| Piece | Composition | Note transcription / arrangement | Permission for the sequence |
|---|---|---|---|
| Symphony No. 5, IV: Adagietto | Gustav Mahler (1860–1911), 1904 | [mooing, score 4230156](https://musescore.com/user/1397281/scores/4230156); harp, two violins, viola, cello, bass | CC0 1.0 |
| Symphony No. 5, I: opening trumpet call | Mahler, 1904 | Our concert-pitch transcription of the pickup and eight bars on printed p. 3 of [Peters plate 9015, Sibley Music Library](https://hdl.handle.net/1802/15744) | Public-domain 1904 score; new transcription dedicated to CC0 1.0 |
| Magnetic Rag | Scott Joplin (1868–1917), 1914 | [Mutopia 441](https://www.mutopiaproject.org/ftp/JoplinS/magnetic/), Kurt Holtrop, original edition | Mutopia explicitly marks the transcription **Public Domain** |
| El Choclo | Ángel Villoldo (1861–1919), 1903 | [bbuyukkarhan, piano score 5885692](https://musescore.com/user/33429668/scores/5885692) | CC0 1.0 |
| Entry of the Gladiators, marching-band excerpt | Julius Fučík (1872–1916), 1897 | Eric Russ / imwoaheric, [score 5733627](https://musescore.com/user/34335505/scores/5733627), “Stands Tune” | CC0 1.0, including the modern arrangement |
| Ikariotikos | Traditional Greek dance, anonymous | ekwesh62, [score 6124814](https://musescore.com/user/34984664/scores/6124814) | CC0 1.0 |
| Bethena, a concert waltz | Joplin, 1905 | [Mutopia 463](https://www.mutopiaproject.org/ftp/JoplinS/bethena/), Magnus Lewis-Smith, original manuscript | Mutopia explicitly marks the transcription **Public Domain** |
| Gymnopédie No. 1 | Erik Satie (1866–1925), 1888 | [Mutopia, SatieE/gymnopedie_1](https://www.mutopiaproject.org/ftp/SatieE/gymnopedie_1/), Evin Robertson, Dover edition | Mutopia explicitly marks the transcription **Public Domain** |
| Ave Maria (Méditation sur le premier prélude de Bach) | Charles Gounod (1818–1893), 1853, on J. S. Bach's Prelude in C | [Mutopia, GounodC/AveMaria-PianoViolin](https://www.mutopiaproject.org/ftp/GounodC/AveMaria-PianoViolin/), Yann Leprince, Heugel 1856 | Mutopia explicitly marks the transcription **Public Domain** |
| Ave Maria (Ellens dritter Gesang), D. 839, Op. 52 No. 6, voice and piano; one strophe, the tune on our violin | Franz Schubert (1797–1828), 1825 (published 1826) | [Mutopia 1054, SchubertF/D839](https://www.mutopiaproject.org/ftp/SchubertF/D839/SchubertF-D839_AveMaria/), Ph. Raynaud (Mutopia-2007/10/13-1054), C.F. Peters (Band I) edition (the record names no editor) | Mutopia explicitly marks the transcription **Public Domain** |
| Suite bergamasque: Clair de lune | Claude Debussy (1862–1918), 1905 | [Mutopia, DebussyC/L75](https://www.mutopiaproject.org/ftp/DebussyC/L75/debussy_Ste_Bergamesq_Clair/), Keith OHara, Fromont 1905 | Mutopia explicitly marks the transcription **Public Domain** |
| Adelita | Francisco Tárrega (1852–1909) | [Mutopia, TarregaF/adelita-duo](https://www.mutopiaproject.org/ftp/TarregaF/adelita-duo/), Jeffrey Olson's two-guitar arrangement, Antich y Tena | Mutopia explicitly marks the arrangement **Public Domain** |
| Berceuse (Dolly, Op. 56) | Gabriel Fauré (1845–1924), 1894 | [Mutopia, FaureG/O56](https://www.mutopiaproject.org/ftp/FaureG/O56/faure_dolly_berceuse/), Mike Blackstock's flute-and-guitar adaptation, Hamelle | Mutopia explicitly marks the adaptation **Public Domain** |
| Symphony No. 9 "From the New World", II: Largo | Antonín Dvořák (1841–1904), 1894 | [julian9284, score 4285886](https://musescore.com/julian9284/scores/4285886) | CC0 1.0 |
| Symphony No. 9 "From the New World", III: Scherzo (Molto vivace) | Dvořák, 1894 | [mike320, score 1509886](https://musescore.com/user/6105546/scores/1509886) | Public Domain Mark 1.0 (the uploader's mark on MuseScore; PDMX records no licence conflict) |
| Symphony No. 9 "From the New World", IV: Allegro con fuoco | Dvořák, 1894 | [mike320, score 1509896](https://musescore.com/user/6105546/scores/1509896) | Public Domain Mark 1.0 (the uploader's mark on MuseScore; PDMX records no licence conflict) |
| Symphony No. 7, II: Allegretto | Ludwig van Beethoven (1770–1827), 1816 | [alexander, score 949716](https://musescore.com/user/15685/scores/949716) | CC0 1.0 |
| Eine kleine Nachtmusik, I: Allegro | Wolfgang Amadeus Mozart (1756–1791), 1827 | [madmax82, score 2225101](https://musescore.com/user/1817676/scores/2225101) | CC0 1.0 |
| Clarinet Concerto K. 622, II: Adagio | Mozart, 1801 | [NekMib_, score 5486316](https://musescore.com/user/16850931/scores/5486316) | CC0 1.0 |
| Piano Sonata No. 8 "Pathétique", II: Adagio cantabile | Beethoven, 1799 | [Mutopia 295](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=295), Chris Sawer, Berners, 1908 (edited by A. Winterberger); Peters, 1910 | Mutopia explicitly marks the transcription **Public Domain** |
| Symphony No. 40, I: Molto allegro | Mozart, 1798 | [Nicolas, score 106251](https://musescore.com/nicolas/scores/106251) | CC0 1.0 |
| Orchestral Suite No. 3: Air (an arrangement for violin and piano) | Johann Sebastian Bach (1685–1750) | [Aan Aditya Banuwarsa, score 4818780](https://musescore.com/user/5402316/scores/4818780) | CC0 1.0 |
| Má vlast: Vltava (The Moldau), piano | Bedřich Smetana (1824–1884), 1879 | [martinmosch12, score 5911315](https://musescore.com/user/32746368/scores/5911315) | CC0 1.0 |
| Liebestraum No. 3 | Franz Liszt (1811–1886), 1850 | [mooing, score 1578986](https://musescore.com/mooing/scores/1578986) | CC0 1.0 |
| Ständchen (Schwanengesang), piano transcription | Franz Schubert (1797–1828), 1829; Liszt, 1840 | [tonic64, score 4907304](https://musescore.com/user/22249306/scores/4907304) | CC0 1.0 |
| Symphony No. 5, III: Valse (piano) | Pyotr Ilyich Tchaikovsky (1840–1893), 1888 | [hmscomp, score 5623928](https://musescore.com/user/24069/scores/5623928) | CC0 1.0 |
| Lohengrin: Bridal Chorus (choir and piano) | Richard Wagner (1813–1883), 1850 | [Nicolas, score 43724](https://musescore.com/nicolas/scores/43724); the voices sung by our choir | CC0 1.0 |
| Hungarian Dance No. 1 (piano) | Johannes Brahms (1833–1897), 1869 | [ÐÑÐ·ÑÐºÐ°Ð½Ñ, score 1386646](https://musescore.com/user/1580161/scores/1386646) | CC0 1.0 |
| Daphnis et Chloé: Introduction (Part I, a reduction) | Maurice Ravel (1875–1937), 1912 | [Derek Benton, score 5888526](https://musescore.com/user/6053266/scores/5888526) | CC0 1.0 |
| Daphnis et Chloé, Part III: Lever du jour, rehearsal 155 to the bar before 158 (19 bars), the title's music | Ravel, 1912; full score, Durand, 1913 | Our concert-pitch transcription of every part from printed pp. 184–193 of the [Durand 1913 full score](https://archive.org/details/imslp-et-chlo-ravel-maurice) (archive.org's mirror of IMSLP): `source/daphnis-155-24.musicxml` and `.mid` | Public-domain 1913 score; new transcription dedicated to CC0 1.0 |
| Boléro | Ravel, 1929 | [darkblue865, score 5173477](https://musescore.com/user/15856401/scores/5173477) | CC0 1.0 |
| The Barber of Seville: Overture | Gioachino Rossini (1792–1868), 1816 | [mike320, score 2540876](https://musescore.com/user/6105546/scores/2540876) | CC0 1.0 |
| Carmen: Prelude (piano four hands) | Georges Bizet (1838–1875), 1875 | [Noah Godard, score 255426](https://musescore.com/user/125838/scores/255426) | CC0 1.0 |
| An der schönen blauen Donau (piano) | Johann Strauss II (1825–1899), 1867 | [hmscomp, score 114435](https://musescore.com/hmscomp/scores/114435) | CC0 1.0 |
| Unter Donner und Blitz (piano) | Strauss II, 1868 | [Mutopia 610](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=610), Stan Sanderson, C. M. Cady, Pub. 1878 | Mutopia explicitly marks the transcription **Public Domain** |
| Radetzky March (small band) | Johann Strauss I (1804–1849), 1848 | [solar, score 153800](https://musescore.com/user/47480/scores/153800) | CC0 1.0 |
| Florentiner March (an arrangement for double reeds) | Julius Fučík (1872–1916), 1907 | [Ian Compton, score 5911596](https://musescore.com/user/9488281/scores/5911596) | CC0 1.0 |
| The Four Seasons, Summer: III Presto | Antonio Vivaldi (1678–1741), 1725 | [bach2practice, score 5573287](https://musescore.com/bach2practice/scores/5573287); the solo violin on our accordion, a bass under the cello | CC0 1.0 |
| Csárdás (orchestra) | Vittorio Monti (1868–1922), 1904 | [TheNightreader, score 1783226](https://musescore.com/thenightreader/scores/1783226) | CC0 1.0 |
| Gianni Schicchi: O mio babbino caro (piano) | Giacomo Puccini (1858–1924), 1918 | [jeronjoseph, score 4416311](https://musescore.com/user/20208436/scores/4416311) | CC0 1.0 |
| La traviata: Brindisi (piano) | Giuseppe Verdi (1813–1901), 1853 | [Mutopia 1215](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1215), Alberto Corella, Calcografía de la 'Nueva Biblioteca Musical Económica', 1857-1869 | Mutopia explicitly marks the transcription **Public Domain** |
| La Paloma (string quartet) | Sebastián Yradier (1809–1865), c. 1863 | [szyhub, score 4816894](https://musescore.com/user/816231/scores/4816894) | CC0 1.0 |
| Santa Lucia (voice and piano) | Teodoro Cottrau (1827–1879), 1849 | [wizarcat, score 5956250](https://musescore.com/user/27649166/scores/5956250); the voice on the mandolin | CC0 1.0 |
| Funiculì, funiculà (two violins) | Luigi Denza (1846–1922), 1880 | [Alexander Evstyugov-Babaev, score 5677874](https://musescore.com/the_alex/scores/5677874); mandolin and guitar | CC0 1.0 |
| Locus iste (SATB) | Anton Bruckner (1824–1896), 1869 | [sangerforum, score 1972546](https://musescore.com/user/3099636/scores/1972546) | CC0 1.0 |
| Nabucco: Va, pensiero (SATB) | Verdi, 1842 | [sangerforum, score 1140631](https://musescore.com/user/3099636/scores/1140631); the voices sung by our choir | CC0 1.0 |
| Melita, "Eternal Father, Strong to Save" (SATB) | John Bacchus Dykes (1823–1876), 1861 | [Mutopia 1260](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1260), Steve Dunlop, www.cyberhymnal.org; sung by our choir | Mutopia explicitly marks the transcription **Public Domain** |
| Pictures at an Exhibition: Promenade | Modest Mussorgsky (1839–1881), 1886; orchestration Maurice Ravel (1875–1937), 1929 | [mike320, score 5273125](https://musescore.com/user/6105546/scores/5273125) | CC0 1.0 |
| Pictures at an Exhibition: The Old Castle | the same | [mike320, score 5273127](https://musescore.com/user/6105546/scores/5273127) | CC0 1.0 |
| Pictures at an Exhibition: Bydło | the same | [mike320, score 5273132](https://musescore.com/user/6105546/scores/5273132) | CC0 1.0 |
| Pictures at an Exhibition: Ballet of the Unhatched Chicks | the same | [mike320, score 5273138](https://musescore.com/user/6105546/scores/5273138) | CC0 1.0 |
| Pictures at an Exhibition: The Hut on Hen's Legs | the same | [mike320, score 5273146](https://musescore.com/user/6105546/scores/5273146) | CC0 1.0 |
| Pictures at an Exhibition: The Great Gate of Kiev | the same | [mike320, score 5273150](https://musescore.com/user/6105546/scores/5273150) | CC0 1.0 |
| Symphony No. 5, I: Allegro con brio | Beethoven, 1809 | [Nicolas, score 29654](https://musescore.com/nicolas/scores/29654) | CC0 1.0 |
| Symphony No. 5, IV: Allegro | Beethoven, 1809 | [ScorePad, score 6128657](https://musescore.com/user/34878656/scores/6128657) | CC0 1.0 |
| Symphony No. 6 "Pathétique", IV: Adagio lamentoso | Tchaikovsky, 1894 | [Jac wang, score 1578536](https://musescore.com/user/339571/scores/1578536) | CC0 1.0 |
| Swan Lake: Entrance of the Guests and Waltz (piano) | Tchaikovsky, 1877 | [Hinci, score 6337136](https://musescore.com/user/29637645/scores/6337136) | CC0 1.0 |
| Piano Concerto No. 3, I (two pianos) | Sergei Rachmaninoff (1873–1943), 1910 | [hmscomp, score 1844011](https://musescore.com/user/24069/scores/1844011) | CC0 1.0 |
| Die Meistersinger von Nürnberg: Prelude (piano, after Hans von Bülow, 1830–1894) | Wagner, 1868 | [Y.Murakami@TYO, score 4801061](https://musescore.com/user/3797871/scores/4801061) | CC0 1.0 |
| Tristan und Isolde: Liebestod (piano) | Wagner, 1860 | [hmscomp, score 846481](https://musescore.com/hmscomp/scores/846481) | CC0 1.0 |
| Die Walküre: Ride of the Valkyries (piano and voices) | Wagner, 1876 | [hmscomp, score 951686](https://musescore.com/hmscomp/scores/951686) | CC0 1.0 |
| Aida: Triumphal March (orchestra and chorus) | Verdi, 1872 | [chiefyblues, score 6031714](https://musescore.com/user/1680641/scores/6031714) | CC0 1.0 |
| Kinderszenen: Träumerei (string quintet) | Robert Schumann (1810–1856), 1839 | [assdlkde, score 5916073](https://musescore.com/user/33861153/scores/5916073) | CC0 1.0 |
| Slavonic Dance Op. 72 No. 1 (an arrangement for wind band) | Dvořák, 1887 | [JasperGoh, score 6353246](https://musescore.com/user/190843/scores/6353246) | CC0 1.0 |
| Brandenburg Concerto No. 2 | Bach, 1850 (Bach-Gesellschaft) | [patzly, score 1634641](https://musescore.com/user/1836451/scores/1634641) | CC0 1.0 |
| Pange lingua (SATB) | Bruckner, 1868 | [Nicolas Rojas, score 1807361](https://musescore.com/user/2317016/scores/1807361) | CC0 1.0 |
| Symphony No. 1, IV | Brahms, 1877 | [jayW, score 91079](https://musescore.com/user/43726/scores/91079) | CC0 1.0 |
| The Hebrides (Fingal's Cave) (an arrangement for wind band) | Felix Mendelssohn (1809–1847), 1833 | [Bob Bolton, score 5937390](https://musescore.com/user/29446660/scores/5937390) | CC0 1.0 |
| Humoresque Op. 101 No. 7 (violin and cello) | Dvořák, 1894 | [AllmusicLab, score 5936751](https://musescore.com/user/33963911/scores/5936751) | CC0 1.0 |
| Rigoletto: La donna è mobile (orchestra) | Verdi, 1851 | [chiefyblues, score 5664313](https://musescore.com/user/1680641/scores/5664313) | CC0 1.0 |
| Coriolan Overture | Beethoven, 1808 | [janjawohl, score 5925510](https://musescore.com/user/26915832/scores/5925510) | CC0 1.0 |
| Egmont Overture | Beethoven, 1810 | [janjawohl, score 5925491](https://musescore.com/user/26915832/scores/5925491) | CC0 1.0 |
| Piano Concerto No. 5 "Emperor", I | Beethoven, 1811 | [leol91417, score 5742868](https://musescore.com/user/29120318/scores/5742868) | CC0 1.0 |
| Piano Concerto No. 5 "Emperor", II | Beethoven, 1811 | [tonic64, score 4205196](https://musescore.com/user/22249306/scores/4205196) | CC0 1.0 |
| Symphony No. 9, I | Beethoven, 1826 | [violin-altair, score 4499721](https://musescore.com/user/337881/scores/4499721) | CC0 1.0 |
| Symphony No. 9, IV (orchestra and chorus) | Beethoven, 1826 | [shilaher67, score 5942325](https://musescore.com/user/34003467/scores/5942325) | CC0 1.0 |
| Water Music (an arrangement for wind band) | Handel (1685–1759), 1733 | [lpwevers, score 5844795](https://musescore.com/user/21735231/scores/5844795) | CC0 1.0 |
| Music for the Royal Fireworks: La Réjouissance | Handel, 1749 | [C_Richardson, score 5769837](https://musescore.com/crichardson/scores/5769837) | CC0 1.0 |
| Oboe Concerto No. 3 in G minor | Handel, 1863 (Händel-Gesellschaft) | [matthewClarkson, score 5848348](https://musescore.com/user/30345247/scores/5848348) | CC0 1.0 |
| Symphony No. 5, II: Stürmisch bewegt | Mahler, 1904 | [mooing, score 4889732](https://musescore.com/user/1397281/scores/4889732) | CC0 1.0 |
| Symphony No. 9, III: Rondo-Burleske (two pianos, four hands) | Mahler, 1912 | [Clarin Pardo, score 193041](https://musescore.com/user/84251/scores/193041) | CC0 1.0 |
| Clarinet Concerto K. 622, I | Mozart, 1801 | [NekMib_, score 5294134](https://musescore.com/user/16850931/scores/5294134) | CC0 1.0 |
| Symphony No. 40, IV | Mozart, 1798 | [eduardomezencio, score 1916356](https://musescore.com/eduardomezencio/scores/1916356) | CC0 1.0 |
| Symphony No. 41 "Jupiter" | Mozart, 1793 | [Vigo KovaÄiÄ, score 4676996](https://musescore.com/user/6755401/scores/4676996) | CC0 1.0 |
| La Gioconda: Dance of the Hours | Amilcare Ponchielli (1834–1886), 1876 | [MikeStokesberry, score 5903108](https://musescore.com/user/15377981/scores/5903108) | CC0 1.0 |
| Swan Lake, Act II: Scene (an arrangement for wind band) | Tchaikovsky, 1877 | [Pringle Abilla, score 5969235](https://musescore.com/user/28335048/scores/5969235) | CC0 1.0 |
| Symphony No. 4, IV | Tchaikovsky, 1878 | [Deyziel, score 5975276](https://musescore.com/user/26806535/scores/5975276) | CC0 1.0 |
| The Nutcracker: Waltz of the Snowflakes | Tchaikovsky, 1892 | [Eva House, score 4982042](https://musescore.com/user/13976176/scores/4982042) | CC0 1.0 |
| The Nutcracker: Dance of the Sugar Plum Fairy (an arrangement for wind band) | Tchaikovsky, 1892 | [Austin Volkmer, score 5892725](https://musescore.com/user/24130321/scores/5892725) | CC0 1.0 |
| Messa da Requiem: Sanctus | Verdi, 1874 | [chiefyblues, score 6302023](https://musescore.com/user/1680641/scores/6302023) | CC0 1.0 |
| Ballade No. 2 | Frédéric Chopin (1810–1849), 1840 | [hmscomp, score 1115241](https://musescore.com/user/24069/scores/1115241) | CC0 1.0 |
| Berceuse, Op. 57 | Chopin, 1845 | [hmscomp, score 932306](https://musescore.com/user/24069/scores/932306) | CC0 1.0 |
| Fantaisie-Impromptu, Op. 66 | Chopin, 1855 | [venson72150, score 6219891](https://musescore.com/user/33306646/scores/6219891) | CC0 1.0 |
| Nocturne Op. 15 No. 2 | Chopin, 1833 | [venson72150, score 6047021](https://musescore.com/user/33306646/scores/6047021) | CC0 1.0 |
| Polonaise Op. 26 No. 1 | Chopin, 1836 | [Y.Murakami@TYO, score 3783671](https://musescore.com/user/3797871/scores/3783671) | CC0 1.0 |
| Bassoon Concerto K. 191: Andante ma adagio | Wolfgang Amadeus Mozart | [Mutopia 686](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=686), Liang Seng, Breitkopf und Härtel, 1880s | Mutopia explicitly marks the transcription **Public Domain** |
| Andante for flute and orchestra K. 315 | Wolfgang Amadeus Mozart | [Mutopia 344](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=344), Maurizio Tomasi, Breitkopf und Härtel | Mutopia explicitly marks the transcription **Public Domain** |
| Horn Concerto No. 2 K. 417: Allegro maestoso | Wolfgang Amadeus Mozart | [Mutopia 901](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=901), Jay Anderson, Breitkopf & Härtel, 1877-1883 | Mutopia explicitly marks the transcription **Public Domain** |
| Fantasia in D minor K. 397 | Wolfgang Amadeus Mozart | [Mutopia 2034](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=2034), Andrés Necochea, 'Mozart Album: Zongorára' Budapest: Zeneműkiadó Vállalat, 1951 | Mutopia explicitly marks the transcription **Public Domain** |
| Symphony No. 25: Allegro con brio | Wolfgang Amadeus Mozart | [Mutopia 1380](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1380), Stelios Samelis, Breitkopf and Hartel (1880) | Mutopia explicitly marks the transcription **Public Domain** |
| Symphony No. 25: Andante | Wolfgang Amadeus Mozart | [Mutopia 1381](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1381), Stelios Samelis, Breitkopf and Hartel (1880) | Mutopia explicitly marks the transcription **Public Domain** |
| Eine kleine Nachtmusik: Rondo | Wolfgang Amadeus Mozart | [Mutopia 2230](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=2230), Mike Blackstock, Breitkopf & Härtel, 1883 | Mutopia explicitly marks the transcription **Public Domain** |
| Clarinet Quintet K. 581: Larghetto | Wolfgang Amadeus Mozart | [Mutopia 337](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=337), Maurizio Tomasi, Breitkopf und Härtel (1883) | Mutopia explicitly marks the transcription **Public Domain** |
| Symphony No. 5: Andante con moto | Ludwig van Beethoven | [Mutopia 1437](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1437), Stelios Samelis (adapted to v2.16 by Johannes Heinecke), Breitkopf and Härtel (1862-1865) | Mutopia explicitly marks the transcription **Public Domain** |
| Intermezzo in A major, Op. 118 No. 2 | Johannes Brahms | [Mutopia 535](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=535), Aron Fay, N. Simrock, 1892 | Mutopia explicitly marks the transcription **Public Domain** |
| A Midsummer Night's Dream: Intermezzo | Felix Mendelssohn | [Mutopia 80](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=80), Felix Braun, Unknown | Mutopia explicitly marks the transcription **Public Domain** |
| 'Στὰ Γιάννινα [μώρ' Καλαματιανή] (In Yannina, Kalamata girl) | Traditional Greek (collected from Mlle Athina, Athènes); harmonised by L.-A. Bourgault-Ducoudray (1840–1910), no. 24 of *Trente mélodies populaires de Grèce et d'Orient*, 1877 | Our own transcription from the [Sibley Music Library scan](https://hdl.handle.net/1802/23748) of the 4th edition (Lemoine, plate 8024.HL), pages 68 (PDF page 92): the voice and the piano's lowest note per beat, checked bar by bar | Public-domain edition; our transcription dedicated to CC0 1.0 |
| Τὰ ματάκια σου τὰ μαῦρα (Your black eyes, black as the olive) | Traditional Greek (collected from Mme Laffon, Smyrne); harmonised by L.-A. Bourgault-Ducoudray (1840–1910), no. 20 of *Trente mélodies populaires de Grèce et d'Orient*, 1877 | Our own transcription from the [Sibley Music Library scan](https://hdl.handle.net/1802/23748) of the 4th edition (Lemoine, plate 8024.HL), pages 56-57 (PDF pages 80-81): the voice and the piano's lowest note per beat, checked bar by bar | Public-domain edition; our transcription dedicated to CC0 1.0 |
| Σὰν παιθάνω 'ς τὸ καράβι (If I die on the ship) | Traditional Greek (collected from M. Mikhali, Athènes); harmonised by L.-A. Bourgault-Ducoudray (1840–1910), no. 26 of *Trente mélodies populaires de Grèce et d'Orient*, 1877 | Our own transcription from the [Sibley Music Library scan](https://hdl.handle.net/1802/23748) of the 4th edition (Lemoine, plate 8024.HL), pages 76-77 (PDF pages 100-101): the voice and the piano's lowest note per beat, checked bar by bar | Public-domain edition; our transcription dedicated to CC0 1.0 |
| Καράβιν ἔν' ἀπὸ τὴ Χιό ("Un brigantin da Scio partì": a brigantine sailed from Chios) | Traditional Greek (collected from M. Skiadaressi, Athènes); harmonised by L.-A. Bourgault-Ducoudray (1840–1910), no. 25 of *Trente mélodies populaires de Grèce et d'Orient*, 1877 | Our own transcription from the [Sibley Music Library scan](https://hdl.handle.net/1802/23748) of the 4th edition (Lemoine, plate 8024.HL), pages 72-75 (PDF pages 96-99): the voice and the piano's lowest note per beat, checked bar by bar | Public-domain edition; our transcription dedicated to CC0 1.0 |
| Ἂν παιθάνω, ῥίψετέ με ("Se morrò, gettato io sia": if I die, throw me in the deep sea; refrain "roum ba, roum balia") | Traditional Greek (collected from Mme Laffon, Smyrne); harmonised by L.-A. Bourgault-Ducoudray (1840–1910), no. 10 of *Trente mélodies populaires de Grèce et d'Orient*, 1877 | Our own transcription from the [Sibley Music Library scan](https://hdl.handle.net/1802/23748) of the 4th edition (Lemoine, plate 8024.HL), pages 30-33 (PDF pages 54-57): the voice and the piano's lowest note per beat, checked bar by bar | Public-domain edition; our transcription dedicated to CC0 1.0 |
| Αὐτὸς ὁ κόσμος εἶν' Τουρκιά ("Ah! Eleni mou") | Traditional Greek (collected from M. Gérasimos, Smyrne); harmonised by L.-A. Bourgault-Ducoudray (1840–1910), no. 3 of *Trente mélodies populaires de Grèce et d'Orient*, 1877 | Our own transcription from the [Sibley Music Library scan](https://hdl.handle.net/1802/23748) of the 4th edition (Lemoine, plate 8024.HL), pages 8-9 (PDF pages 32-33): the voice and the piano's lowest note per beat, checked bar by bar | Public-domain edition; our transcription dedicated to CC0 1.0 |
| Τὰ ματάκια σου τὰ μαῦρα (Your eyes are black and sweet: "Son sì neri gli occhi tuoi"; refrain "amán, amán") | Traditional Greek (collected from Mme Laffon, Smyrne); harmonised by L.-A. Bourgault-Ducoudray (1840–1910), no. 8 of *Trente mélodies populaires de Grèce et d'Orient*, 1877 | Our own transcription from the [Sibley Music Library scan](https://hdl.handle.net/1802/23748) of the 4th edition (Lemoine, plate 8024.HL), pages 22-24 (PDF pages 46-48): the voice and the piano's lowest note per beat, checked bar by bar | Public-domain edition; our transcription dedicated to CC0 1.0 |
| Νύσταξαν τὰ ματάκια μου (My eyes grew sleepy) | Traditional Greek (collected from Mme Laffon, Smyrne); harmonised by L.-A. Bourgault-Ducoudray (1840–1910), no. 18 of *Trente mélodies populaires de Grèce et d'Orient*, 1877 | Our own transcription from the [Sibley Music Library scan](https://hdl.handle.net/1802/23748) of the 4th edition (Lemoine, plate 8024.HL), pages 53 (PDF page 77): the voice and the piano's lowest note per beat, checked bar by bar | Public-domain edition; our transcription dedicated to CC0 1.0 |
| Ἕνα πουλάκι ("Un augellin": a little bird wept at dawn) | Traditional Greek (collected from Mme Laffon, Smyrne); harmonised by L.-A. Bourgault-Ducoudray (1840–1910), no. 7 of *Trente mélodies populaires de Grèce et d'Orient*, 1877 | Our own transcription from the [Sibley Music Library scan](https://hdl.handle.net/1802/23748) of the 4th edition (Lemoine, plate 8024.HL), pages 19-21 (PDF pages 43-45): the voice and the piano's lowest note per beat, checked bar by bar | Public-domain edition; our transcription dedicated to CC0 1.0 |
| Ἄστραψεν ἡ Ἀνατολή (Lightning in the east: a cradle song, "rock the child, nurse") | Traditional Greek (collected from Mme Laffon, Smyrne); harmonised by L.-A. Bourgault-Ducoudray (1840–1910), no. 13 of *Trente mélodies populaires de Grèce et d'Orient*, 1877 | Our own transcription from the [Sibley Music Library scan](https://hdl.handle.net/1802/23748) of the 4th edition (Lemoine, plate 8024.HL), pages 42-43 (PDF pages 66-67): the voice and the piano's lowest note per beat, checked bar by bar | Public-domain edition; our transcription dedicated to CC0 1.0 |

CC0: <https://creativecommons.org/publicdomain/zero/1.0/>.

**The rule** (the user's, from 20 November 2026). A piece ships when both hold:

1. **The composition is in the public domain**, in the United States (published 95 or more years
   ago: in 2026, in 1930 or earlier) and in the European Union (its composer, and anyone whose part
   of it is used: a co-composer, arranger, orchestrator or completer, died 70 or more years ago: in
   2026, in 1955 or earlier).
   Anything not in the public domain needs the user's explicit approval, piece by piece.
2. **The note sequence is free to use**: a MuseScore score in PDMX marked CC0 with
   `license_conflict=False`; a Mutopia edition marked Public Domain; or our own transcription
   from a public-domain score scan, dedicated to CC0.

There is no further margin. Ravel (died 1937) qualifies: *Daphnis et Chloé* (published 1912) and
*Boléro* (composed 1928, published 1929) are public domain in the US, and have been in the EU since
2008 (France's wartime extensions have also run out). 'O sole mio does not: a Turin court recognised Alfredo
Mazzucchi (died 1972) as its co-composer. Traditional music is no licence for a modern
arrangement: the sequence still needs (2), as the Ikariotikos sequence's CC0 does.

The MuseScore sequences were obtained from the MIDI and metadata archives of
[PDMX v9, June 2025](https://zenodo.org/records/15571083), by Phillip Long, Zachary Novack,
Julian McAuley and Taylor Berg-Kirkpatrick. Dataset metadata is
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); the individual scores have the separate permissions above. Each selected
CSV row has `license_conflict=False`; the stored score metadata agrees with its public
CC0 designation and lists no copyright claims. `source/licences.json` preserves the
source URLs, named uploaders, licence URLs and SHA-256 hashes of the exact shipped MIDI.
The original Mutopia RDF permission records (two for the first radio pieces and five for the Hotel
Ancora's evening set, fetched 13 November 2026; four for the wider repertoire, fetched 19 November
2026; one for Schubert's Ave Maria, fetched 21 November 2026) are included beside their MIDI files.
Dataset MIDI was converted, instrument assignments changed as described below, and only
a small subset of metadata retained. This is not an endorsement by any source author.

## Performance changes and limits

* Adagietto retains the imported timing, expressive note velocities and CC7/CC11 gain
  at note boundaries. Harp and all five string sections remain separate. This is the
  whole imported movement, not a repeated invented phrase. MIDI is a transcription,
  not a critical edition; the converter does not interpret printed expression marks.
* The first-movement sample is **only the opening solo call**, not the whole movement
  or its orchestral entry. Written B-flat trumpet pitches are transposed down a tone.
  The score says “In gemessenem Schritt. Streng. Wie ein Kondukt.” The pickups are
  sixteenth-note triplets. The fourth long note is E4 concert pitch; the final tied
  C-sharp5 is one continuous note. Earlier versions used overly broad pickups and
  incorrectly retriggered that tie. Coarse timing and three-point effort contours in
  `opening-performance.json` now annotate this solo excerpt explicitly.
* The title's music is the opening of Part III of *Daphnis et Chloé* (Lever du jour), rehearsal
  155 to the bar before 158: 19 bars, 73.2 s at the score's crotchet = 50, ending where the
  theme's first statement has sunk away (158 begins the next phrase). Every part of the full
  score is transcribed at sounding pitch (clarinets in A and E-flat, bass clarinet, horns in F,
  alto flute, cor anglais, contrabassoon, contrabasses and celesta are written as they sound).
  The earlier catalogue piece under this name was the ballet's *Introduction* in a reduction; it
  keeps its place on the radio under its own title.
  - Transcribed, not printed: the harp glissandi are written out string by string on the pedal
    setting the printed accidentals show; the three solo violins' harmonics are at their sounding
    pitches; grace notes are short notes; trills are marked on the written note. Slurs, hairpins
    and dynamics are not in the MusicXML: the arrangement (`daphnis_lever` in
    `tools/music_pack.py`) carries the printed dynamics bar by bar.
  - Least certain (quiet colour or inner doubling): the piccolo's bird calls in bars 14–16,
    flute 1's solo calls in bars 13 and 16, and the upper note of trombones 1–2 at 157.
  - Our synthesizer lacks some of the score's instruments. Each plays on the nearest timbre:

    | Score | Synthesizer |
    |---|---|
    | Alto flute, piccolo | flute |
    | Cor anglais | oboe |
    | Clarinet in E-flat, bass clarinet | clarinet |
    | Trombones, tuba | brass (the horn timbre) |
    | Celesta | piano, very softly |
    | Three solo violins, in harmonics | strings |
    | Bass drum (one held stroke left from before 155) | not played |
* Schubert's Ave Maria is the whole song as the Mutopia edition prints it: 43 bars, an introduction,
  the three strophes of the German text (after Walter Scott's *The Lady of the Lake*; 312 voice notes;
  the piano as printed, 2,023 notes) and the postlude, with no repeat cut and no note added. The
  edition's MIDI carries a placeholder tempo (the quarter note 2.5 s, 24 to the minute, which makes
  the song 7 minutes); it is played at 34 to the minute ("Sehr langsam"; the score gives no number),
  with a ritardando into the last line of each strophe and a broader one through the postlude
  (`schubert_points` in `tools/music_performance.py`), the song 5 min 27 s. The data keeps the voice's
  line on a violin; wherever the piece is played (the radio's classical round, the hotel's set one
  evening in three) the hotel singer's procedural voice (`src/singer.jo`) sings that line over the
  piano, and the violin does not play under her (`SUNG` in `tools/music_pack.py`; remove the entry,
  repack and rebalance for the violin version).
* Magnetic Rag is explicitly a **foxtrot arrangement of a rag**, not labelled an
  original foxtrot. All source piano pitches/rhythms are retained, at quarter=116;
  upper notes use clarinet, lower piano/bass, with light banjo doubling and a drum beat.
* El Choclo's piano notes become accordion/piano/bass. This is the imported short
  piano arrangement, not a claim to every repeat of the original published score.
* The march retains Eric Russ's short band arrangement. Saxophones use our reed voice;
  percussion is procedural. It is not the entire original march.
* Ikariotikos uses the licensed melody on paired plucked strings, with a quiet octave
  accordion doubling; no new chord progression is substituted for the melody.
* Bethena retains the source piano notes and tempo. MIDI sustain/pitch-bend effects are
  not interpreted; note release and hall decay supply a modest sustain tail.
* The wider repertoire (from *Symphony No. 9: Largo* in the table on) keeps each source's notes
  and instruments, except: Vivaldi's *Summer* gives the solo violin to the accordion and doubles
  the cello's low notes an octave down on the bass; the voices of *Va, pensiero*, *Melita* and the
  *Lohengrin* chorus (exported as piano or clarinet parts) are sung by the choir; *Santa Lucia*'s
  voice is played on the mandolin; *Funiculì, funiculà*'s two violins become mandolin and guitar.
  The New World's Scherzo and Finale leave out the one percussion part the synthesizer has no voice
  for (the Scherzo's triangle, the Finale's single crash cymbal stroke); trombones and the bass
  trombone play on the brass timbre.
  Each piece is played at one level, measured to sit at the hand-set pieces' loudness
  (`tools/music_level.py`, `levels.json`). On the radio, a station plays its style's pieces one
  after another, each from its start (`src/radio_synth.jo` radio_pool).
* Every other evening the Hotel Ancora's trio (accordion, upright piano, bass) plays *Summer*,
  *El Choclo* and *Santa Lucia* live (`src/bar_band.jo` bar_trio): the tune on the accordion, the
  low line on the bass, the other parts on the piano. No notes are added or changed.
* The Greek songs of Bourgault-Ducoudray's 1877 collection are our own transcriptions from the
  public-domain scan, made from it alone (no other edition, recording or MIDI consulted): the voice
  line as printed and the piano's lowest note per beat (the right hand is not transcribed). The
  piano-only introductions and interludes are therefore cut to a bar or so of the bass
  (`tools/music_pack.py` greek_song); the dances take the tune on the bouzouki with a quiet
  accordion an octave below, the lyrical songs on the violin, over a guitar. The transcriptions
  are dedicated to CC0 1.0 (the user's decision of 21 November 2026: our transcriptions of
  public-domain music may be kept in the repository).
* Per-note start/end gain follows velocity and CC7/11. Controller curves within a note
  are approximated by a straight ramp, not reproduced exactly.

* The radio's Gymnopédie No. 1 (`gymnopedie-orchestra`) is the same Mutopia source, scored by
  `tools/music_pack.py` in the manner of Debussy's orchestration (1897, public domain): the tune on
  the oboe and then, from bar 22, the flute; the second-beat chords on the harp with muted strings
  holding them; the bass notes on the harp and the low strings. Only the instrumentation follows
  Debussy; no notes are taken from his score.
* The Hotel Ancora's evening set (not on the radio) is arranged for its small band:
  Gymnopédie No. 1 is Satie's piano texture, the pianist alone; Ave Maria keeps the source violin and piano (the bar's singer
  takes the violin's line, which then plays at half level); Clair de lune is the source piano
  alone, its rubato, dynamics, pedal and voicing from an annotated performance
  (`clair-de-lune-performance.json`, written by `tools/clair_performance.py`; see
  `docs/music-performance.md`); Adelita's two guitars become a mandolin-like plucked voice (the tune) and a guitar;
  the Berceuse's flute becomes the violin over the guitar. All source pitches and rhythms are
  kept; the interpretation pass adds gentle phrase timing and a final ritard. The Mutopia MIDI
  files play each piece once, without the printed repeats.

Rebuild: `python tools/music_pack.py`. Additional repertoire must meet the rule above: the
composition **and** the sequence. Do not substitute an unlicensed MIDI
just because its underlying composition is old.

Dataset publications: Long et al., *PDMX: A Large-Scale Public Domain MusicXML Dataset for Symbolic Music Processing*, ICASSP 2025, [doi:10.1109/ICASSP49660.2025.10890217](https://doi.org/10.1109/ICASSP49660.2025.10890217); Xu et al., *Generating Symbolic Music from Natural Language Prompts using an LLM-Enhanced Dataset*, 2024, [arXiv:2410.02084](https://arxiv.org/abs/2410.02084). Only the source score MIDI is used here, not generated examples or model output.

The interpretation pass changes timing, articulation and dynamics, not these licensed
pitch sequences. Its decisions are recorded in `performance.json`; see
`docs/music-performance.md`. `instruments.json` contains scalar parameters for the game's
procedural oscillators and envelopes, packed by `tools/music_timbres.py`. It contains no
PCM, recorded sample loops, waveform phases or measured impulse responses.
Its 17th family, the 1920s upright piano (`MUSIC_UPRIGHT`, a honky-tonk), was fitted the same
way as the others (per-partial amplitudes, measured over the unison's beat, and two decay rates at
three velocities and seven pitches; inharmonicity, attack, release; loudness kept across the
keyboard), plus a body response fitted from a reference phrase and the unison's spacing (two equal
strings 5 cents apart, `UPRIGHT_DETUNE_CENTS` in src/music_synth.jo), to FluidR3 GM's Honky-tonk
Piano (bank 0, program 3; the same soundfont file, SHA-256 74594e8f...a1bc1cb0, as the measurements
above; copyright Frank Wen, permissive licence). Its notes and phrases were rendered through
FluidSynth offline in scratch for measurement only; no soundfont data or rendered audio is in this
repository, only the fitted numbers.
