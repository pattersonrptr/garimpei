import { SearchForm } from "@/components/SearchForm";
import { TopBar } from "@/components/TopBar";

export default function NotFound() {
  return (
    <>
      <TopBar withSearch={false} />
      <main className="container empty">
        <h1>Página não encontrada.</h1>
        <p className="muted" style={{ margin: "12px 0 24px" }}>
          O livro pode não estar no nosso catálogo ainda. Busque pelo título, pelo
          autor ou pelo ISBN.
        </p>
        <SearchForm />
      </main>
    </>
  );
}
