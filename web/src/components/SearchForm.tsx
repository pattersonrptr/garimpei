/** A plain GET form: works with no JavaScript, and the results URL is shareable. */
export function SearchForm({
  defaultValue = "",
  autoFocus = false,
}: {
  defaultValue?: string;
  autoFocus?: boolean;
}) {
  return (
    <form className="search" action="/busca" method="get" role="search">
      <label htmlFor="q" className="visually-hidden">
        Título, autor ou ISBN
      </label>
      <input
        id="q"
        name="q"
        type="search"
        defaultValue={defaultValue}
        placeholder="Título, autor ou ISBN"
        autoFocus={autoFocus}
        autoComplete="off"
        enterKeyHint="search"
        required
        minLength={2}
      />
      <button className="button" type="submit">
        Buscar
      </button>
    </form>
  );
}
