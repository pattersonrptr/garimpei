import Link from "next/link";

import { SearchForm } from "@/components/SearchForm";
import { TopBar } from "@/components/TopBar";

export default function Home() {
  return (
    <>
      <TopBar withSearch={false} />
      <main className="container hero">
        <h1>Livro novo ou usado: ache o melhor preço.</h1>
        <p>
          Comparamos livrarias e sebos todos os dias. Você vê o novo e o usado lado a
          lado, e quanto dá para economizar.
        </p>
        <SearchForm autoFocus />
        <p className="hints muted">
          Experimente: <Link href="/busca?q=tolkien">Tolkien</Link>,{" "}
          <Link href="/busca?q=cem%20anos">Cem anos de solidão</Link> ou um ISBN.
        </p>
      </main>
    </>
  );
}
