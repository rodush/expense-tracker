export function formatAmount(amount) {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "EUR",
  }).format(Number(amount));
}
