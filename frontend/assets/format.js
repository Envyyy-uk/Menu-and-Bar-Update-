/* ==========================================================================
   Спільне форматування: гроші, години розкладу, дата відкриття.

   Потрібне і гостю, і панелі, і екрану кухні — тому живе окремо.
   Час усюди в поясі закладу, не пристрою.
   ========================================================================== */

/* Ціна — надрукований факт, як і назва страви: гість платить £11.50 незалежно
   від того, якою мовою читає меню. Тому фунт форматуємо по-британськи, а не
   мовою гостя («11,50 GBP» плутає більше, ніж допомагає). */
const MONEY_LOCALE = { GBP: 'en-GB', EUR: 'de-DE', USD: 'en-US' };

const money = (pence, currency, lang) =>
  new Intl.NumberFormat(MONEY_LOCALE[currency] || lang || 'en', {
    style: 'currency', currency: currency || 'GBP'
  }).format((pence || 0) / 100);

/** Дата відкриття людською мовою: «15 серпня, 12:00» */
function formatUntil(stamp, lang) {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(stamp || '');
  if (!m) return stamp || '';
  // збираємо в UTC і форматуємо в UTC — інакше пояс пристрою зсуне дату
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]));
  return new Intl.DateTimeFormat(lang, {
    day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit',
    hourCycle: 'h23', timeZone: 'UTC'
  }).format(d);
}

/** «Пн, Нд 12:00–22:00 · Вт–Сб 12:00–17:30» */
function describeSchedule(ranges, lang) {
  if (!ranges || !ranges.length) return '';
  const names = t('sched.days', lang).split(',');
  return ranges.map(r => {
    // тиждень читаємо з понеділка, а не з неділі
    const weekPos = d => (d + 6) % 7;
    const sorted = [...(r.days || [])].sort((a, b) => weekPos(a) - weekPos(b));
    const runs = [];
    sorted.forEach(d => {
      const last = runs[runs.length - 1];
      if (last && weekPos(d) === weekPos(last[last.length - 1]) + 1) last.push(d);
      else runs.push([d]);
    });
    const days = runs.map(run => run.length > 2
      ? `${names[run[0]]}–${names[run[run.length - 1]]}`
      : run.map(d => names[d]).join(', ')).join(', ');
    return `${days} ${r.from}–${r.to}`;
  }).join(' · ');
}

/** Час у поясі закладу — для годинника в шапці панелі й кухні */
function venueClock(timezone, lang) {
  return new Intl.DateTimeFormat(lang || 'en', {
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZone: timezone
  }).format(new Date());
}
