/* ==========================================================================
   14 обов'язкових алергенів (ЄС / UK FSA) — назви та пояснення 6 мовами.

   Перенесено з референсу. Ключі приведені до тих, якими говорять дані
   (`cereals-gluten`, `tree-nuts`), щоб між меню й базою не було перекладача.
   ========================================================================== */

const ALLERGENS = {
  'cereals-gluten': {
    icon: '🌾', short: { uk: 'ГЛ', en: 'GL', es: 'GL', it: 'GL', de: 'GL', ru: 'ГЛ' },
    t: { uk: 'Злаки з глютеном', en: 'Cereals containing gluten', es: 'Cereales con gluten', it: 'Cereali con glutine', de: 'Glutenhaltiges Getreide', ru: 'Злаки с глютеном' },
    note: {
      uk: 'Пшениця, жито, ячмінь, овес: хліб, паста, паніровка, борошняні соуси, пиво.',
      en: 'Wheat, rye, barley, oats: bread, pasta, breading, flour-thickened sauces, beer.',
      es: 'Trigo, centeno, cebada, avena: pan, pasta, empanados, salsas con harina, cerveza.',
      it: 'Frumento, segale, orzo, avena: pane, pasta, panature, salse legate con farina, birra.',
      de: 'Weizen, Roggen, Gerste, Hafer: Brot, Pasta, Panade, mehlgebundene Saucen, Bier.',
      ru: 'Пшеница, рожь, ячмень, овёс: хлеб, паста, панировка, мучные соусы, пиво.'
    }
  },
  crustaceans: {
    icon: '🦐', short: { uk: 'РК', en: 'CR', es: 'CR', it: 'CR', de: 'KR', ru: 'РК' },
    t: { uk: 'Ракоподібні', en: 'Crustaceans', es: 'Crustáceos', it: 'Crostacei', de: 'Krebstiere', ru: 'Ракообразные' },
    note: {
      uk: 'Креветки, лобстер, краб — у тому числі сушені у соусах.',
      en: 'Prawns, lobster, crab — including dried shrimp in sauces.',
      es: 'Gambas, bogavante, cangrejo — incluidas las gambas secas en salsas.',
      it: 'Gamberi, astice, granchio — compresi i gamberi essiccati nelle salse.',
      de: 'Garnelen, Hummer, Krabbe — auch getrocknete Garnelen in Saucen.',
      ru: 'Креветки, лобстер, краб — в том числе сушёные в соусах.'
    }
  },
  eggs: {
    icon: '🥚', short: { uk: 'ЯЙ', en: 'EG', es: 'HU', it: 'UO', de: 'EI', ru: 'ЯЙ' },
    t: { uk: 'Яйця', en: 'Eggs', es: 'Huevos', it: 'Uova', de: 'Eier', ru: 'Яйца' },
    note: {
      uk: 'Майонез, айолі, голландський соус, тісто, білок у коктейлях.',
      en: 'Mayonnaise, aioli, hollandaise, batters, egg white in cocktails.',
      es: 'Mayonesa, alioli, holandesa, masas, clara en cócteles.',
      it: 'Maionese, aioli, olandese, impasti, albume nei cocktail.',
      de: 'Mayonnaise, Aioli, Hollandaise, Teige, Eiweiß in Cocktails.',
      ru: 'Майонез, айоли, голландский соус, тесто, белок в коктейлях.'
    }
  },
  fish: {
    icon: '🐟', short: { uk: 'РИ', en: 'FI', es: 'PE', it: 'PE', de: 'FI', ru: 'РЫ' },
    t: { uk: 'Риба', en: 'Fish', es: 'Pescado', it: 'Pesce', de: 'Fisch', ru: 'Рыба' },
    note: {
      uk: 'Також анчоуси в соусах — зеленому, «Цезарі», вустерському.',
      en: 'Including anchovies in sauces — salsa verde, Caesar, Worcestershire.',
      es: 'Incluidas las anchoas en salsas: verde, César, Worcestershire.',
      it: 'Comprese le acciughe nelle salse: verde, Caesar, Worcestershire.',
      de: 'Auch Sardellen in Saucen — Salsa verde, Caesar, Worcestershire.',
      ru: 'В том числе анчоусы в соусах — зелёном, «Цезаре», вустерском.'
    }
  },
  peanuts: {
    icon: '🥜', short: { uk: 'АР', en: 'PN', es: 'CA', it: 'AR', de: 'ER', ru: 'АР' },
    t: { uk: 'Арахіс', en: 'Peanuts', es: 'Cacahuetes', it: 'Arachidi', de: 'Erdnüsse', ru: 'Арахис' },
    note: {
      uk: 'Арахісова паста, олія, кондитерські вироби зі спільної лінії.',
      en: 'Peanut butter, peanut oil, confectionery from a shared line.',
      es: 'Crema de cacahuete, aceite de cacahuete, dulces de línea compartida.',
      it: 'Burro di arachidi, olio di arachidi, dolci da linea condivisa.',
      de: 'Erdnussbutter, Erdnussöl, Süßwaren aus geteilter Fertigung.',
      ru: 'Арахисовая паста, масло, кондитерка со совместной линии.'
    }
  },
  soya: {
    icon: '🫘', short: { uk: 'СО', en: 'SY', es: 'SO', it: 'SO', de: 'SO', ru: 'СО' },
    t: { uk: 'Соя', en: 'Soybeans', es: 'Soja', it: 'Soia', de: 'Soja', ru: 'Соя' },
    note: {
      uk: 'Соєвий соус, місо, соєвий лецитин у шоколаді.',
      en: 'Soy sauce, miso, soya lecithin in chocolate.',
      es: 'Salsa de soja, miso, lecitina de soja en el chocolate.',
      it: 'Salsa di soia, miso, lecitina di soia nel cioccolato.',
      de: 'Sojasauce, Miso, Sojalecithin in Schokolade.',
      ru: 'Соевый соус, мисо, соевый лецитин в шоколаде.'
    }
  },
  milk: {
    icon: '🥛', short: { uk: 'МО', en: 'MK', es: 'LE', it: 'LA', de: 'MI', ru: 'МО' },
    t: { uk: 'Молоко', en: 'Milk', es: 'Leche', it: 'Latte', de: 'Milch', ru: 'Молоко' },
    note: {
      uk: 'Вершкове масло, вершки, сири, морозиво. Рибу й м’ясо часто фінішують маслом.',
      en: 'Butter, cream, cheeses, ice cream. Fish and meat are often finished with butter.',
      es: 'Mantequilla, nata, quesos, helado. Pescado y carne suelen terminarse con mantequilla.',
      it: 'Burro, panna, formaggi, gelato. Pesce e carne sono spesso rifiniti al burro.',
      de: 'Butter, Sahne, Käse, Eis. Fisch und Fleisch werden oft mit Butter vollendet.',
      ru: 'Сливочное масло, сливки, сыры, мороженое. Рыбу и мясо часто финишируют маслом.'
    }
  },
  'tree-nuts': {
    icon: '🌰', short: { uk: 'ГО', en: 'NT', es: 'FS', it: 'FG', de: 'NÜ', ru: 'ОР' },
    t: { uk: 'Горіхи', en: 'Tree nuts', es: 'Frutos secos de cáscara', it: 'Frutta a guscio', de: 'Schalenfrüchte', ru: 'Орехи' },
    note: {
      uk: 'Волоські, мигдаль, фундук і горіхові сиропи. Кокос у частині країн також рахують горіхом.',
      en: 'Walnuts, almonds, hazelnuts and nut syrups. Coconut is classed as a nut in some countries.',
      es: 'Nueces, almendras, avellanas y siropes de fruto seco. En algunos países el coco cuenta como fruto seco.',
      it: 'Noci, mandorle, nocciole e sciroppi di frutta secca. In alcuni paesi il cocco è classificato come frutta a guscio.',
      de: 'Walnüsse, Mandeln, Haselnüsse und Nusssirupe. Kokos gilt in manchen Ländern als Schalenfrucht.',
      ru: 'Грецкие, миндаль, фундук и ореховые сиропы. В ряде стран кокос также относят к орехам.'
    }
  },
  celery: {
    icon: '🥬', short: { uk: 'СЕ', en: 'CE', es: 'AP', it: 'SE', de: 'SE', ru: 'СЕ' },
    t: { uk: 'Селера', en: 'Celery', es: 'Apio', it: 'Sedano', de: 'Sellerie', ru: 'Сельдерей' },
    note: {
      uk: 'Корінь селери, бульйони, суміші спецій.',
      en: 'Celeriac, stocks, spice blends.',
      es: 'Apionabo, caldos, mezclas de especias.',
      it: 'Sedano rapa, brodi, mix di spezie.',
      de: 'Knollensellerie, Fonds, Gewürzmischungen.',
      ru: 'Корень сельдерея, бульоны, смеси специй.'
    }
  },
  mustard: {
    icon: '🟡', short: { uk: 'ГІ', en: 'MU', es: 'MO', it: 'SE', de: 'SF', ru: 'ГО' },
    t: { uk: 'Гірчиця', en: 'Mustard', es: 'Mostaza', it: 'Senape', de: 'Senf', ru: 'Горчица' },
    note: {
      uk: 'Діжонська гірчиця, заправки, майонез.',
      en: 'Dijon mustard, dressings, mayonnaise.',
      es: 'Mostaza de Dijon, aliños, mayonesa.',
      it: 'Senape di Digione, condimenti, maionese.',
      de: 'Dijon-Senf, Dressings, Mayonnaise.',
      ru: 'Дижонская горчица, заправки, майонез.'
    }
  },
  sesame: {
    icon: '⚪', short: { uk: 'КУ', en: 'SE', es: 'SÉ', it: 'SS', de: 'SA', ru: 'КУ' },
    t: { uk: 'Кунжут', en: 'Sesame', es: 'Sésamo', it: 'Sesamo', de: 'Sesam', ru: 'Кунжут' },
    note: {
      uk: 'Кунжутна олія, тахіні, чорний кунжут, булочки з посипкою.',
      en: 'Sesame oil, tahini, black sesame, seeded buns.',
      es: 'Aceite de sésamo, tahini, sésamo negro, panecillos con semillas.',
      it: 'Olio di sesamo, tahini, sesamo nero, panini ai semi.',
      de: 'Sesamöl, Tahini, schwarzer Sesam, Brötchen mit Saaten.',
      ru: 'Кунжутное масло, тахини, чёрный кунжут, булочки с посыпкой.'
    }
  },
  sulphites: {
    icon: '🍷', short: { uk: 'СУ', en: 'SU', es: 'SU', it: 'SO', de: 'SU', ru: 'СУ' },
    t: { uk: 'Сульфіти (SO₂)', en: 'Sulphur dioxide & sulphites', es: 'Dióxido de azufre y sulfitos', it: 'Anidride solforosa e solfiti', de: 'Schwefeldioxid & Sulfite', ru: 'Сульфиты (SO₂)' },
    note: {
      uk: 'Вино, оцет, в’ялені м’ясні вироби, сухофрукти, оброблена картопля, соки.',
      en: 'Wine, vinegar, cured meats, dried fruit, processed potatoes, juices.',
      es: 'Vino, vinagre, embutidos, fruta seca, patata procesada, zumos.',
      it: 'Vino, aceto, salumi, frutta secca, patate lavorate, succhi.',
      de: 'Wein, Essig, Pökelwaren, Trockenobst, verarbeitete Kartoffeln, Säfte.',
      ru: 'Вино, уксус, вяленые мясные изделия, сухофрукты, обработанный картофель, соки.'
    }
  },
  lupin: {
    icon: '🌸', short: { uk: 'ЛЮ', en: 'LU', es: 'AL', it: 'LU', de: 'LU', ru: 'ЛЮ' },
    t: { uk: 'Люпин', en: 'Lupin', es: 'Altramuces', it: 'Lupini', de: 'Lupinen', ru: 'Люпин' },
    note: {
      uk: 'Люпинове борошно у випічці та безглютенових сумішах.',
      en: 'Lupin flour in baked goods and gluten-free blends.',
      es: 'Harina de altramuz en bollería y mezclas sin gluten.',
      it: 'Farina di lupino nei prodotti da forno e nelle miscele senza glutine.',
      de: 'Lupinenmehl in Backwaren und glutenfreien Mischungen.',
      ru: 'Люпиновая мука в выпечке и безглютеновых смесях.'
    }
  },
  molluscs: {
    icon: '🦪', short: { uk: 'МЛ', en: 'MO', es: 'MO', it: 'MO', de: 'WT', ru: 'МЛ' },
    t: { uk: 'Молюски', en: 'Molluscs', es: 'Moluscos', it: 'Molluschi', de: 'Weichtiere', ru: 'Моллюски' },
    note: {
      uk: 'Устриці, гребінці, восьминіг, кальмар.',
      en: 'Oysters, scallops, octopus, squid.',
      es: 'Ostras, vieiras, pulpo, calamar.',
      it: 'Ostriche, capesante, polpo, calamaro.',
      de: 'Austern, Jakobsmuscheln, Oktopus, Tintenfisch.',
      ru: 'Устрицы, гребешки, осьминог, кальмар.'
    }
  }
};

const ALLERGEN_KEYS = Object.keys(ALLERGENS);

const aName  = (k, lang) => (ALLERGENS[k] ? ALLERGENS[k].t[lang] || ALLERGENS[k].t.en : k);
const aShort = (k, lang) => (ALLERGENS[k] ? ALLERGENS[k].short[lang] || ALLERGENS[k].short.en : k);
const aNote  = (k, lang) => (ALLERGENS[k] ? ALLERGENS[k].note[lang] || ALLERGENS[k].note.en : '');
