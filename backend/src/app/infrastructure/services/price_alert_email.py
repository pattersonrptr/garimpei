"""
Content of the price alert email, shared by every email provider.

Product titles and URLs come from third-party listings, so everything
interpolated into the HTML is escaped.
"""

from dataclasses import dataclass
from html import escape


@dataclass(frozen=True)
class PriceAlertEmail:
    subject: str
    html: str
    text: str


def _brl(value: float) -> str:
    # Same format as the subject recorded in notification logs by the use cases.
    return f"R$ {value:,.2f}"


def build_price_alert_email(
    search_term: str,
    product_title: str,
    product_price: float,
    max_price: float,
    product_url: str,
    source_website_name: str,
    rate_limit_minutes: int,
) -> PriceAlertEmail:
    savings = max_price - product_price
    subject = (
        f"🎯 Oportunidade! {search_term} por {_brl(product_price)}"
        f" no {source_website_name}"
    )

    term = escape(search_term)
    title = escape(product_title)
    site = escape(source_website_name)
    url = escape(product_url, quote=True)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .header {{ background: #1976d2; color: #fff; padding: 20px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .body {{ padding: 24px; }}
        .highlight {{ background: #e8f5e9; border-left: 4px solid #4caf50; padding: 16px; margin: 16px 0; border-radius: 4px; }}
        .price {{ font-size: 28px; color: #2e7d32; font-weight: bold; }}
        .savings {{ color: #f57c00; font-weight: bold; }}
        .btn {{ display: inline-block; background: #1976d2; color: #fff; padding: 12px 24px; text-decoration: none; border-radius: 4px; margin-top: 16px; }}
        .footer {{ background: #f4f4f4; padding: 16px; text-align: center; font-size: 12px; color: #999; }}
        .details {{ margin: 16px 0; }}
        .details td {{ padding: 4px 8px; }}
        .details td:first-child {{ font-weight: bold; color: #555; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Oportunidade encontrada!</h1>
        </div>
        <div class="body">
            <p>Olá! Encontramos um produto abaixo do seu preço alvo para a busca <strong>"{term}"</strong>.</p>

            <div class="highlight">
                <p style="margin:0 0 8px 0;"><strong>{title}</strong></p>
                <p class="price" style="margin:0;">{_brl(product_price)}</p>
                <p class="savings" style="margin:8px 0 0 0;">Economia de {_brl(savings)} em relação ao seu alerta ({_brl(max_price)})</p>
            </div>

            <table class="details">
                <tr><td>Site:</td><td>{site}</td></tr>
                <tr><td>Preço máximo do alerta:</td><td>{_brl(max_price)}</td></tr>
                <tr><td>Preço encontrado:</td><td>{_brl(product_price)}</td></tr>
            </table>

            <a href="{url}" class="btn">Ver produto →</a>
        </div>
        <div class="footer">
            <p>Você recebeu este e-mail porque configurou um alerta de preço no Garimpei.</p>
            <p>Limite de envio: 1 e-mail por alerta a cada {rate_limit_minutes} minutos.</p>
        </div>
    </div>
</body>
</html>"""

    text = (
        f'Oportunidade encontrada para a busca "{search_term}"!\n\n'
        f"{product_title}\n"
        f"Preço: {_brl(product_price)} (seu alerta: {_brl(max_price)}, "
        f"economia de {_brl(savings)})\n"
        f"Site: {source_website_name}\n\n"
        f"Ver produto: {product_url}\n"
    )
    return PriceAlertEmail(subject=subject, html=html, text=text)
