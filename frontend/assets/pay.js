/* ==========================================================================
   Оплата на нашій сторінці: Apple Pay, Google Pay і картка.

   Гість сидить за столом із телефоном у руці. Перекидати його на чужий домен
   і чекати, поки він повернеться, — зайвий крок, на якому губляться
   замовлення. Тому картка й гаманці живуть у тому ж аркуші, що й кошик.

   Номер картки ми не бачимо: поля малює Stripe.js у своєму фреймі, нам
   дістається лише `client_secret`. Це і тримає нас у межах SAQ A.

   Головне правило не змінилося: **успішний платіж у браузері не робить
   замовлення оплаченим**. `paid` виставляє вебхук. Гість може згорнути
   вкладку рівно між списанням і відповіддю — і замовлення все одно дійде.
   ========================================================================== */

const STRIPE_JS = 'https://js.stripe.com/v3/';

let stripeLoading = null;

/** Stripe.js вантажимо лише тоді, коли справді треба платити: гість, який
    просто читає меню, не має тягнути чужий скрипт. */
function loadStripeJs() {
  if (window.Stripe) return Promise.resolve(window.Stripe);
  if (stripeLoading) return stripeLoading;
  stripeLoading = new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = STRIPE_JS;
    s.async = true;
    s.onload = () => (window.Stripe ? resolve(window.Stripe) : reject(new Error('Stripe.js')));
    s.onerror = () => reject(new Error('Stripe.js'));
    document.head.appendChild(s);
  });
  return stripeLoading;
}

/**
 * Аркуш оплати.
 *
 * @param {object} pay   відповідь /checkout: client_secret, publishable_key,
 *                       account_id, amount_pence, currency
 * @param {object} data  меню (потрібне для валюти й перемальовування)
 * @param {function} onPaid  викликається, коли Stripe підтвердив списання
 */
async function openPaymentSheet(pay, data, onPaid) {
  document.querySelectorAll('.sheet').forEach(n => n.remove());
  const sheet = el('div', 'sheet');
  const box = el('div', 'sheet-box pay-box');
  sheet.appendChild(box);
  document.body.appendChild(sheet);

  box.appendChild(el('h2', null, esc(t('pay.title', LANG))));
  box.appendChild(el('p', 'pay-total',
    `${esc(t('cart.total', LANG))}: <b>${esc(money(pay.amount_pence, pay.currency, LANG))}</b>`));

  const status = el('p', 'pay-status');
  const wallets = el('div', 'pay-wallets');
  const divider = el('p', 'pay-or', esc(t('pay.or', LANG)));
  const card = el('div', 'pay-card');
  // Поки гаманці не відповіли — не показуємо ні їх, ні розділювач: порожня
  // рамка над карткою виглядає як зламана кнопка.
  wallets.hidden = true;
  divider.hidden = true;
  box.append(status, wallets, divider, card);

  const submit = el('button', 'primary wide', esc(t('pay.submit', LANG)));
  submit.type = 'button';
  submit.disabled = true;
  box.appendChild(submit);

  const close = el('button', 'wide', esc(t('pay.later', LANG)));
  close.type = 'button';
  close.addEventListener('click', () => sheet.remove());
  box.appendChild(close);

  let Stripe;
  try {
    Stripe = await loadStripeJs();
  } catch (e) {
    // Мережа впала або скрипт заблокований — кажемо прямо, а не показуємо
    // порожній аркуш: гість має розуміти, що платити зараз нема чим.
    status.className = 'pay-status warn';
    status.textContent = t('pay.noscript', LANG);
    return;
  }

  // При direct charge елементи створюються від імені закладу: без
  // `stripeAccount` гаманець не з'явиться взагалі.
  const stripe = Stripe(pay.publishable_key, { stripeAccount: pay.account_id });
  const elements = stripe.elements({
    clientSecret: pay.client_secret,
    appearance: { theme: document.documentElement.dataset.theme === 'light' ? 'stripe' : 'night' }
  });

  let done = false;
  const finish = async (result) => {
    if (done) return;
    if (result.error) {
      status.className = 'pay-status warn';
      status.textContent = result.error.message || t('pay.failed', LANG);
      submit.disabled = false;
      submit.textContent = t('pay.submit', LANG);
      return;
    }
    done = true;
    // Списання пройшло — але оплаченим замовлення робить вебхук, не ми.
    status.className = 'pay-status ok';
    status.textContent = t('pay.sent', LANG);
    submit.remove();
    setTimeout(() => sheet.remove(), 1200);
    onPaid();
  };

  const confirm = (extra) => stripe.confirmPayment({
    elements,
    clientSecret: pay.client_secret,
    confirmParams: { return_url: location.href },
    // Повертаємось на цю ж сторінку тільки якщо банк вимагає 3-D Secure
    redirect: 'if_required',
    ...extra
  }).then(finish, err => finish({ error: err }));

  // --- Apple Pay / Google Pay ----------------------------------------------
  // Який саме гаманець показати, вирішує Stripe за пристроєм і браузером.
  // Ми не питаємо «це айфон?» — це відповідь, яка застаріває.
  try {
    const express = elements.create('expressCheckout', {
      buttonTheme: { applePay: 'black', googlePay: 'black' }
    });
    express.on('ready', ev => {
      const has = ev && ev.availablePaymentMethods
        && Object.values(ev.availablePaymentMethods).some(Boolean);
      // Гаманця немає — не показуємо ні кнопок, ні слова «або».
      wallets.hidden = !has;
      divider.hidden = !has;
    });
    express.on('confirm', () => {
      status.textContent = t('pay.working', LANG);
      confirm();
    });
    express.mount(wallets);
  } catch (e) {
    wallets.hidden = true;
    divider.hidden = true;
  }

  // --- картка ---------------------------------------------------------------
  const payment = elements.create('payment', { layout: 'tabs' });
  payment.on('ready', () => { submit.disabled = false; });
  payment.mount(card);

  submit.addEventListener('click', () => {
    submit.disabled = true;
    submit.textContent = t('pay.working', LANG);
    status.className = 'pay-status';
    status.textContent = '';
    confirm();
  });
}
