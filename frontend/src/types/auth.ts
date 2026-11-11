export interface User {
  id: string
  email: string
  name: string | null
  isVerified: boolean
}

export interface RegisterInput {
  email: string
  password: string
  name?: string
}
