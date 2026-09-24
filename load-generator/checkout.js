import http from 'k6/http';
import { check, sleep } from 'k6';
export const options = { vus: 3, duration: '2m' };
export default function () {
  const response = http.get(`http://frontend-api:8000/checkout?slow=${Math.random() < 0.2}`);
  check(response, { 'checkout completed': (r) => r.status === 200 });
  sleep(0.5);
}
