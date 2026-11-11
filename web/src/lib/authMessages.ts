/** The backend's sign-in and sign-up errors, as the user reads them. */

export const MIN_PASSWORD_LENGTH = 8;

export interface ApiError {
  status: number;
  code?: string;
  pointer?: string;
}

export function signInMessage(error: ApiError): string {
  if (error.status === 400 || error.status === 401 || error.status === 422) {
    return "E-mail, usuário ou senha incorretos.";
  }
  return "Não foi possível entrar agora. Tente de novo em instantes.";
}

export function signUpMessage(error: ApiError): string {
  if (error.code === "USERNAME_TAKEN") return "Esse nome de usuário já está em uso.";
  if (error.code === "EMAIL_TAKEN") return "Já existe uma conta com esse e-mail. Entre com ele.";
  if (error.status === 422 && error.pointer?.includes("email")) return "Confira o e-mail.";
  if (error.status === 422) return "Confira os dados do formulário.";
  return "Não foi possível criar a conta agora. Tente de novo em instantes.";
}

export interface SignUpFields {
  username: string;
  email: string;
  password: string;
}

/** Checks done before calling the backend; null when the form is fine. */
export function signUpProblem(fields: SignUpFields): string | null {
  if (!fields.username || !fields.email || !fields.password) return "Preencha todos os campos.";
  if (/\s/.test(fields.username)) return "O nome de usuário não pode ter espaços.";
  if (!fields.email.includes("@")) return "Confira o e-mail.";
  if (fields.password.length < MIN_PASSWORD_LENGTH) {
    return `A senha precisa de pelo menos ${MIN_PASSWORD_LENGTH} caracteres.`;
  }
  return null;
}
