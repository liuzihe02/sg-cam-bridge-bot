const API_URL = import.meta.env.PROD
  ? ''  // Same origin in production
  : 'http://localhost:8000';

export async function getGame(chatId: string, userId: string) {
  const res = await fetch(
    `${API_URL}/api/game?chat_id=${chatId}&user_id=${userId}`
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: 'Failed to get game' }));
    throw new Error(err.message || 'Failed to get game');
  }
  return res.json();
}

export async function playCard(chatId: string, userId: string, card: string) {
  try {
    const res = await fetch(`${API_URL}/api/play`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, user_id: userId, card })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ message: 'Failed to play card' }));
      alert(err.message || 'Something went wrong. Try again!');
      throw new Error(err.message);
    }
  } catch (e) {
    console.error('Play card failed:', e);
    throw e;
  }
}

export async function makeBid(chatId: string, userId: string, bid: string) {
  try {
    const res = await fetch(`${API_URL}/api/bid`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, user_id: userId, bid })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ message: 'Failed to make bid' }));
      alert(err.message || 'Something went wrong. Try again!');
      throw new Error(err.message);
    }
  } catch (e) {
    console.error('Make bid failed:', e);
    throw e;
  }
}

export async function callPartner(chatId: string, userId: string, card: string) {
  try {
    const res = await fetch(`${API_URL}/api/call`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, user_id: userId, card })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ message: 'Failed to call partner' }));
      alert(err.message || 'Something went wrong. Try again!');
      throw new Error(err.message);
    }
  } catch (e) {
    console.error('Call partner failed:', e);
    throw e;
  }
}
