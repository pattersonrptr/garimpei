import type { Metadata } from "next";
import Link from "next/link";

import { deleteAlertAction, setActiveAction } from "@/app/actions/alerts";
import { signOutAction } from "@/app/actions/session";
import { PriceForm } from "@/components/AlertForms";
import { TopBar } from "@/components/TopBar";
import { listMyAlerts } from "@/lib/alertsApi";
import { bookPath } from "@/lib/format";
import {
  type MyAlert,
  alertKind,
  noticeCount,
  noticeLine,
  targetLine,
  verdictBadge,
} from "@/lib/myAlerts";
import { requireSession } from "@/lib/session";

export const metadata: Metadata = { title: "Meus alertas", robots: { index: false } };

type Props = {
  searchParams: Promise<{ criado?: string; excluido?: string; erro?: string }>;
};

const FLASH: Record<string, string> = {
  criado: "Alerta criado. Vamos te avisar por e-mail quando o preço chegar lá.",
  excluido: "Alerta excluído.",
};
const ERRORS: Record<string, string> = {
  limite: "Você chegou ao limite de alertas ativos. Pause ou exclua outro antes de retomar este.",
  salvar: "Não foi possível salvar agora. Tente de novo em instantes.",
};

function productHref(alert: MyAlert): string | null {
  const product = alert.product;
  return product?.isbn13 ? bookPath(product.isbn13, product.title) : null;
}

function AlertCard({ alert }: { alert: MyAlert }) {
  const href = productHref(alert);
  const line = targetLine(alert);
  const badge = verdictBadge(alert.today?.verdict);
  const [last, ...older] = alert.notices.recent;
  const price = alert.maxPrice.toFixed(2).replace(".", ",");
  return (
    <li className={alert.isActive ? "alert-card" : "alert-card paused"}>
      <div className="alert-product">
        {alert.product?.coverUrl && <img src={alert.product.coverUrl} alt="" width={56} />}
        <div>
          <p className="muted small">
            {alertKind(alert)}
            {!alert.isActive && <span className="tag">Pausado</span>}
          </p>
          <p className="alert-title">
            {href ? <Link href={href}>{alert.product?.title}</Link> : alert.product?.title ?? "Produto removido"}
          </p>
          <p className={line.reached ? "good target" : "target"}>{line.text}</p>
          {badge && <span className={`badge ${badge.tone}`}>{badge.label}</span>}
        </div>
      </div>

      <div className="alert-notices small">
        {last ? (
          <details>
            <summary>
              {noticeCount(alert.notices.total)} · último em {noticeLine(last)}
            </summary>
            {older.length > 0 && (
              <ul>
                {older.map((notice, i) => (
                  <li key={`${notice.sentAt}-${i}`}>{noticeLine(notice)}</li>
                ))}
              </ul>
            )}
          </details>
        ) : (
          <p className="muted">{noticeCount(0)}</p>
        )}
      </div>

      <div className="alert-actions">
        <form action={setActiveAction}>
          <input type="hidden" name="id" value={alert.id} />
          <input type="hidden" name="active" value={String(!alert.isActive)} />
          <button className="button secondary small" type="submit">
            {alert.isActive ? "Pausar" : "Retomar"}
          </button>
        </form>
        <details className="inline-action">
          <summary className="button secondary small">Mudar preço</summary>
          <PriceForm id={alert.id} price={price} />
        </details>
        <details className="inline-action">
          <summary className="button secondary small danger">Excluir</summary>
          <form action={deleteAlertAction} className="confirm">
            <input type="hidden" name="id" value={alert.id} />
            <p className="small">Excluir este alerta? Não dá para desfazer.</p>
            <button className="button small danger-solid" type="submit">
              Sim, excluir
            </button>
          </form>
        </details>
      </div>
    </li>
  );
}

export default async function MyAlertsPage({ searchParams }: Props) {
  const session = await requireSession("/alertas");
  const params = await searchParams;
  const alerts = await listMyAlerts(session, "/alertas");
  const flash = params.criado ? FLASH.criado : params.excluido ? FLASH.excluido : null;
  const error = params.erro ? ERRORS[params.erro] ?? ERRORS.salvar : null;

  return (
    <>
      <TopBar />
      <main className="container my-alerts">
        <div className="my-alerts-header">
          <h1>Meus alertas</h1>
          <form action={signOutAction}>
            <button className="link-button small" type="submit">
              Sair ({session.claims.sub})
            </button>
          </form>
        </div>
        {flash && (
          <p className="notice" role="status">
            {flash}
          </p>
        )}
        {error && <p className="form-error">{error}</p>}
        {alerts.length === 0 ? (
          <div className="empty">
            <p>Você ainda não tem alertas.</p>
            <p className="muted">
              Busque um produto e toque em <strong>“Me avise quando baixar”</strong> na página dele.
            </p>
          </div>
        ) : (
          <ul className="alert-list">
            {alerts.map((alert) => (
              <AlertCard key={alert.id} alert={alert} />
            ))}
          </ul>
        )}
      </main>
    </>
  );
}
