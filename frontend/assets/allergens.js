/* ==========================================================================
   14 обов'язкових алергенів (ЄС / UK FSA) — назви та пояснення 6 мовами.

   Перенесено з референсу. Ключі приведені до тих, якими говорять дані
   (`cereals-gluten`, `tree-nuts`), щоб між меню й базою не було перекладача.
   ========================================================================== */

const ALLERGENS = {
  'cereals-gluten': {
    icon: '🌾', short: { uk: 'ГЛ', en: 'GL',    ru: 'ГЛ' },
    t: { uk: 'Злаки з глютеном', en: 'Cereals containing gluten',    ru: 'Злаки с глютеном' },
    note: {
      uk: 'Пшениця, жито, ячмінь, овес: хліб, паста, паніровка, борошняні соуси, пиво.',
      en: 'Wheat, rye, barley, oats: bread, pasta, breading, flour-thickened sauces, beer.',   
      ru: 'Пшеница, рожь, ячмень, овёс: хлеб, паста, панировка, мучные соусы, пиво.'
    }
  },
  crustaceans: {
    icon: '🦐', short: { uk: 'РК', en: 'CR',    ru: 'РК' },
    t: { uk: 'Ракоподібні', en: 'Crustaceans',    ru: 'Ракообразные' },
    note: {
      uk: 'Креветки, лобстер, краб — у тому числі сушені у соусах.',
      en: 'Prawns, lobster, crab — including dried shrimp in sauces.',   
      ru: 'Креветки, лобстер, краб — в том числе сушёные в соусах.'
    }
  },
  eggs: {
    icon: '🥚', short: { uk: 'ЯЙ', en: 'EG',    ru: 'ЯЙ' },
    t: { uk: 'Яйця', en: 'Eggs',    ru: 'Яйца' },
    note: {
      uk: 'Майонез, айолі, голландський соус, тісто, білок у коктейлях.',
      en: 'Mayonnaise, aioli, hollandaise, batters, egg white in cocktails.',   
      ru: 'Майонез, айоли, голландский соус, тесто, белок в коктейлях.'
    }
  },
  fish: {
    icon: '🐟', short: { uk: 'РИ', en: 'FI',    ru: 'РЫ' },
    t: { uk: 'Риба', en: 'Fish',    ru: 'Рыба' },
    note: {
      uk: 'Також анчоуси в соусах — зеленому, «Цезарі», вустерському.',
      en: 'Including anchovies in sauces — salsa verde, Caesar, Worcestershire.',   
      ru: 'В том числе анчоусы в соусах — зелёном, «Цезаре», вустерском.'
    }
  },
  peanuts: {
    icon: '🥜', short: { uk: 'АР', en: 'PN',    ru: 'АР' },
    t: { uk: 'Арахіс', en: 'Peanuts',    ru: 'Арахис' },
    note: {
      uk: 'Арахісова паста, олія, кондитерські вироби зі спільної лінії.',
      en: 'Peanut butter, peanut oil, confectionery from a shared line.',   
      ru: 'Арахисовая паста, масло, кондитерка со совместной линии.'
    }
  },
  soya: {
    icon: '🫘', short: { uk: 'СО', en: 'SY',    ru: 'СО' },
    t: { uk: 'Соя', en: 'Soybeans',    ru: 'Соя' },
    note: {
      uk: 'Соєвий соус, місо, соєвий лецитин у шоколаді.',
      en: 'Soy sauce, miso, soya lecithin in chocolate.',   
      ru: 'Соевый соус, мисо, соевый лецитин в шоколаде.'
    }
  },
  milk: {
    icon: '🥛', short: { uk: 'МО', en: 'MK',    ru: 'МО' },
    t: { uk: 'Молоко', en: 'Milk',    ru: 'Молоко' },
    note: {
      uk: 'Вершкове масло, вершки, сири, морозиво. Рибу й м’ясо часто фінішують маслом.',
      en: 'Butter, cream, cheeses, ice cream. Fish and meat are often finished with butter.',   
      ru: 'Сливочное масло, сливки, сыры, мороженое. Рыбу и мясо часто финишируют маслом.'
    }
  },
  'tree-nuts': {
    icon: '🌰', short: { uk: 'ГО', en: 'NT',    ru: 'ОР' },
    t: { uk: 'Горіхи', en: 'Tree nuts',    ru: 'Орехи' },
    note: {
      uk: 'Волоські, мигдаль, фундук і горіхові сиропи. Кокос у частині країн також рахують горіхом.',
      en: 'Walnuts, almonds, hazelnuts and nut syrups. Coconut is classed as a nut in some countries.',   
      ru: 'Грецкие, миндаль, фундук и ореховые сиропы. В ряде стран кокос также относят к орехам.'
    }
  },
  celery: {
    icon: '🥬', short: { uk: 'СЕ', en: 'CE',    ru: 'СЕ' },
    t: { uk: 'Селера', en: 'Celery',    ru: 'Сельдерей' },
    note: {
      uk: 'Корінь селери, бульйони, суміші спецій.',
      en: 'Celeriac, stocks, spice blends.',   
      ru: 'Корень сельдерея, бульоны, смеси специй.'
    }
  },
  mustard: {
    icon: '🟡', short: { uk: 'ГІ', en: 'MU',    ru: 'ГО' },
    t: { uk: 'Гірчиця', en: 'Mustard',    ru: 'Горчица' },
    note: {
      uk: 'Діжонська гірчиця, заправки, майонез.',
      en: 'Dijon mustard, dressings, mayonnaise.',   
      ru: 'Дижонская горчица, заправки, майонез.'
    }
  },
  sesame: {
    icon: '⚪', short: { uk: 'КУ', en: 'SE',    ru: 'КУ' },
    t: { uk: 'Кунжут', en: 'Sesame',    ru: 'Кунжут' },
    note: {
      uk: 'Кунжутна олія, тахіні, чорний кунжут, булочки з посипкою.',
      en: 'Sesame oil, tahini, black sesame, seeded buns.',   
      ru: 'Кунжутное масло, тахини, чёрный кунжут, булочки с посыпкой.'
    }
  },
  sulphites: {
    icon: '🍷', short: { uk: 'СУ', en: 'SU',    ru: 'СУ' },
    t: { uk: 'Сульфіти (SO₂)', en: 'Sulphur dioxide & sulphites',    ru: 'Сульфиты (SO₂)' },
    note: {
      uk: 'Вино, оцет, в’ялені м’ясні вироби, сухофрукти, оброблена картопля, соки.',
      en: 'Wine, vinegar, cured meats, dried fruit, processed potatoes, juices.',   
      ru: 'Вино, уксус, вяленые мясные изделия, сухофрукты, обработанный картофель, соки.'
    }
  },
  lupin: {
    icon: '🌸', short: { uk: 'ЛЮ', en: 'LU',    ru: 'ЛЮ' },
    t: { uk: 'Люпин', en: 'Lupin',    ru: 'Люпин' },
    note: {
      uk: 'Люпинове борошно у випічці та безглютенових сумішах.',
      en: 'Lupin flour in baked goods and gluten-free blends.',   
      ru: 'Люпиновая мука в выпечке и безглютеновых смесях.'
    }
  },
  molluscs: {
    icon: '🦪', short: { uk: 'МЛ', en: 'MO',    ru: 'МЛ' },
    t: { uk: 'Молюски', en: 'Molluscs',    ru: 'Моллюски' },
    note: {
      uk: 'Устриці, гребінці, восьминіг, кальмар.',
      en: 'Oysters, scallops, octopus, squid.',   
      ru: 'Устрицы, гребешки, осьминог, кальмар.'
    }
  }
};

const ALLERGEN_KEYS = Object.keys(ALLERGENS);

const aName  = (k, lang) => (ALLERGENS[k] ? ALLERGENS[k].t[lang] || ALLERGENS[k].t.en : k);
const aShort = (k, lang) => (ALLERGENS[k] ? ALLERGENS[k].short[lang] || ALLERGENS[k].short.en : k);
const aNote  = (k, lang) => (ALLERGENS[k] ? ALLERGENS[k].note[lang] || ALLERGENS[k].note.en : '');
