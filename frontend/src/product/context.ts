import { createContext, useContext } from 'react'

import type { ProductApi } from './types'
import { unavailableProductApi } from './unavailable'

export const ProductContext = createContext<ProductApi>(unavailableProductApi)

export function useProduct(): ProductApi {
  return useContext(ProductContext)
}
