"""
Content of the price alert email, shared by every email provider.

Same identity as the site (gold, ink and paper; prices like "R$ 17,46";
store names as people know them). Styles are inline and the layout uses
tables, because many e-mail clients drop <style> blocks.

Product titles and URLs come from third-party listings, so everything
interpolated into the HTML is escaped.
"""

from dataclasses import dataclass
from html import escape

from src.app.alerts.notification_text import alert_subject, brl, store_name

# The site's tokens (web/src/app/globals.css)
GOLD = "#ffc928"
INK = "#1a1712"
PAPER = "#fffdf6"
SAND = "#ece5d2"
MUTED = "#6a6355"
GOOD = "#1f7a3d"
FONT = "'DM Sans', 'Segoe UI', Arial, sans-serif"


@dataclass(frozen=True)
class PriceAlertEmail:
    subject: str
    html: str
    text: str


def build_price_alert_email(
    search_term: str,
    product_title: str,
    product_price: float,
    max_price: float,
    product_url: str,
    source_website_name: str,
    rate_limit_minutes: int,
) -> PriceAlertEmail:
    below = max_price - product_price
    store = store_name(source_website_name)
    subject = alert_subject(search_term, product_price, source_website_name)

    title = escape(product_title)
    shop = escape(store)
    url = escape(product_url, quote=True)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(subject)}</title>
</head>
<body style="margin:0; padding:0; background:{PAPER}; font-family:{FONT}; color:{INK};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAPER};">
<tr><td align="center" style="padding:24px 12px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px; background:#ffffff; border:1px solid {SAND}; border-radius:16px; overflow:hidden;">
    <tr><td style="background:{GOLD}; padding:18px 24px; font-size:22px; font-weight:800; color:{INK};">Garimpei</td></tr>
    <tr><td style="padding:24px;">
      <h1 style="margin:0 0 8px; font-size:24px; line-height:1.25; color:{INK};">O preço baixou!</h1>
      <p style="margin:0 0 20px; font-size:16px; line-height:1.5;">Um alerta seu chegou no preço que você queria.</p>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{SAND}; border-radius:12px;">
        <tr><td style="padding:18px 20px;">
          <p style="margin:0 0 6px; font-size:16px; font-weight:700;">{title}</p>
          <p style="margin:0; font-size:30px; font-weight:800; color:{GOOD};">{brl(product_price)}</p>
          <p style="margin:6px 0 0; font-size:15px;">na {shop} · <strong style="color:{GOOD};">{brl(below)} abaixo do seu alvo</strong> ({brl(max_price)})</p>
        </td></tr>
      </table>
      <table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:24px;">
        <tr><td style="background:{INK}; border-radius:12px;">
          <a href="{url}" style="display:inline-block; padding:14px 28px; font-size:16px; font-weight:700; color:{GOLD}; text-decoration:none;">Ver na loja</a>
        </td></tr>
      </table>
      <p style="margin:20px 0 0; font-size:13px; color:{MUTED};">Confira o valor final na loja antes de comprar.</p>
    </td></tr>
    <tr><td style="padding:16px 24px; border-top:1px solid {SAND}; font-size:12px; line-height:1.5; color:{MUTED};">
      Você recebeu este e-mail porque criou um alerta de preço no Garimpei. Para pausar, mudar o preço ou excluir, abra <strong>Meus alertas</strong> no site.<br>
      No máximo 1 e-mail por alerta a cada {rate_limit_minutes} minutos.
    </td></tr>
  </table>
</td></tr>
</table>
</body>
</html>"""

    text = (
        "O preço baixou!\n\n"
        f"{product_title}\n"
        f"{brl(product_price)} na {store} "
        f"({brl(below)} abaixo do seu alvo de {brl(max_price)})\n\n"
        f"Ver na loja: {product_url}\n\n"
        "Confira o valor final na loja antes de comprar.\n"
        "Para pausar, mudar o preço ou excluir, abra Meus alertas no Garimpei.\n"
    )
    return PriceAlertEmail(subject=subject, html=html, text=text)
