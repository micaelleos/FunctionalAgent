// Textos da interface (Constituição X.1): centralizados para futura internacionalização.
export const t = {
  app: { name: 'SpecFlow AI' },
  nav: {
    chat: 'Chat',
    account: 'Minha conta',
    about: 'Sobre',
    signOut: 'Sair',
    userMenu: 'Menu do usuário',
  },
  login: {
    title: 'Entrar no SpecFlow AI',
    google: 'Entrar com Google',
    or: 'ou',
    email: 'E-mail',
    password: 'Senha',
    submit: 'Entrar',
    forgot: 'Esqueci minha senha',
    noAccount: 'Ainda não tem conta?',
    signUp: 'Cadastre-se',
    sharedLogin:
      'O login é o mesmo dos outros apps do portfólio: se você já tem conta em um deles, use-a aqui.',
  },
  signup: {
    title: 'Criar conta',
    name: 'Nome',
    email: 'E-mail',
    password: 'Senha (mínimo de 6 caracteres)',
    submit: 'Criar conta',
    hasAccount: 'Já tem conta?',
    signIn: 'Entrar',
  },
  verify: {
    title: 'Confirme seu e-mail',
    body: (email: string) =>
      `Enviamos um link de confirmação para ${email}. Abra o link e depois clique em "Já confirmei".`,
    done: 'Já confirmei',
    resend: 'Reenviar e-mail',
    resent: 'E-mail reenviado. Confira também a caixa de spam.',
    stillUnverified: 'Ainda não encontramos a confirmação. Abra o link do e-mail e tente de novo.',
    other: 'Entrar com outra conta',
  },
  reset: {
    title: 'Redefinir senha',
    body: 'Informe seu e-mail e enviaremos um link para criar uma nova senha.',
    email: 'E-mail',
    submit: 'Enviar link',
    sent: 'Se houver uma conta com esse e-mail, você receberá o link em alguns minutos.',
    back: 'Voltar para o login',
  },
  account: {
    title: 'Minha conta',
    profile: 'Perfil',
    name: 'Nome',
    email: 'E-mail',
    since: 'Conta no SpecFlow AI desde',
    exportTitle: 'Meus dados',
    exportBody: 'Baixe um arquivo JSON com todos os seus dados no SpecFlow AI.',
    exportButton: 'Baixar meus dados',
    deleteTitle: 'Excluir minha conta',
    deleteBody:
      'Apaga todos os seus dados do SpecFlow AI (perfil, conversas, conexões). Não dá para desfazer.',
    deleteShared:
      'Seu login (e-mail e senha ou Google) é compartilhado com os outros apps do portfólio e continua valendo neles. Se entrar de novo aqui, você começa do zero.',
    deleteConfirmLabel: 'Digite EXCLUIR para confirmar',
    deleteWord: 'EXCLUIR',
    deleteButton: 'Excluir meus dados',
    deleted: 'Seus dados do SpecFlow AI foram excluídos.',
  },
  chat: {
    title: 'Chat',
    soon: 'O agente chega em breve (F05/F06). Enquanto isso, confira sua conta.',
  },
  status: {
    checking: 'Verificando a API…',
    ok: 'API: ok',
    details: (version: string, env: string) => `(versão ${version}, ambiente ${env})`,
    down: 'API indisponível',
  },
  common: { loading: 'Carregando…', error: 'Algo deu errado.' },
  errors: {
    'auth/invalid-credential': 'E-mail ou senha incorretos.',
    'auth/wrong-password': 'E-mail ou senha incorretos.',
    'auth/user-not-found': 'E-mail ou senha incorretos.',
    'auth/invalid-email': 'E-mail inválido.',
    'auth/email-already-in-use': 'Já existe uma conta com esse e-mail. Entre ou redefina a senha.',
    'auth/weak-password': 'Senha muito fraca: use pelo menos 6 caracteres.',
    'auth/too-many-requests': 'Muitas tentativas. Espere alguns minutos e tente de novo.',
    'auth/network-request-failed': 'Sem conexão. Verifique sua internet e tente de novo.',
    'auth/popup-closed-by-user': 'A janela do Google foi fechada antes de terminar.',
    'auth/popup-blocked':
      'O navegador bloqueou a janela do Google. Permita pop-ups e tente de novo.',
    unauthenticated: 'Sua sessão expirou. Entre de novo.',
    'email-not-verified': 'Confirme seu e-mail para continuar.',
  } as Record<string, string>,
} as const

export function errorMessage(error: unknown): string {
  const code =
    typeof error === 'object' && error !== null && 'code' in error ? String(error.code) : ''
  return t.errors[code] ?? t.common.error
}
