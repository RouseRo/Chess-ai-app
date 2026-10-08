const { randomUUID } = require('node:crypto');
const { test, expect } = require('@playwright/test');
const jqueryPath = require.resolve('jquery/dist/jquery.min.js');

const appBaseUrl = process.env.EMAIL_GAMES_BASE_URL || 'http://127.0.0.1:18080';
const mailpitBaseUrl = process.env.MAILPIT_BASE_URL || 'http://127.0.0.1:18025';
const testPassword = 'LocalChessTest2026!';

async function registerUser(request, username, email) {
  const response = await request.post(`${appBaseUrl}/auth/register`, {
    data: { username, email, password: testPassword }
  });
  expect(response.ok()).toBeTruthy();
  expect((await response.json()).success).toBeTruthy();
}

async function loginUser(request, username) {
  const loginResponse = await request.post(`${appBaseUrl}/auth/login`, {
    data: { username, password: testPassword }
  });
  expect(loginResponse.ok()).toBeTruthy();
  const login = await loginResponse.json();
  expect(login.success).toBeTruthy();
  return login.token;
}

async function waitForMessage(request, recipient, subject) {
  let messageId;
  await expect.poll(async () => {
    const response = await request.get(`${mailpitBaseUrl}/api/v1/messages?limit=50`);
    if (!response.ok()) return '';
    const result = await response.json();
    const match = (result.messages || []).find(message =>
      message.Subject === subject &&
      (message.To || []).some(address => address.Address.toLowerCase() === recipient.toLowerCase())
    );
    messageId = match && match.ID;
    return messageId || '';
  }, { timeout: 20000, intervals: [250, 500, 1000] }).toBeTruthy();

  const response = await request.get(`${mailpitBaseUrl}/api/v1/message/${messageId}`);
  expect(response.ok()).toBeTruthy();
  return response.json();
}

async function openGamePage(browser, gameId, username, request) {
  const page = await browser.newPage();
  await page.route('https://code.jquery.com/jquery-3.7.1.min.js', route =>
    route.fulfill({ path: jqueryPath, contentType: 'application/javascript' })
  );
  await page.goto(`/email-game.html?game_id=${gameId}`);
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(testPassword);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.locator('#game')).toBeVisible();
  return page;
}

async function movePiece(page, from, to) {
  await page.locator(`#board .square-${from} .piece-417db`).dragTo(
    page.locator(`#board .square-${to}`)
  );
}

async function expectTurnSideAtBottom(page, color) {
  await expect.poll(() => page.locator('#board [data-square]').first().getAttribute('data-square'))
    .toBe(color === 'White' ? 'a8' : 'h1');
}

test('community player list can be resized', async ({ browser, request }) => {
  const username = `resize_user_${randomUUID().slice(0, 8)}`;
  const targetUsername = `resize_target_${randomUUID().slice(0, 8)}`;
  await registerUser(request, username, `${username}@example.test`);
  await registerUser(request, targetUsername, `${targetUsername}@example.test`);
  const token = await loginUser(request, username);

  const page = await browser.newPage();
  await page.addInitScript(({ authToken, currentUser }) => {
    localStorage.setItem('authToken', authToken);
    localStorage.setItem('currentUser', currentUser);
  }, { authToken: token, currentUser: username });
  await page.goto('/');
  const goToGame = page.getByRole('button', { name: 'Go to Game' });
  if (await goToGame.isVisible().catch(() => false)) await goToGame.click();
  await page.getByRole('button', { name: /Community/ }).click();

  const sidebar = page.locator('#community-users-sidebar');
  const resizer = page.getByRole('separator', { name: 'Resize player list' });
  const initialWidth = await sidebar.evaluate(element => element.getBoundingClientRect().width);
  const bounds = await resizer.boundingBox();
  await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + 40);
  await page.mouse.down();
  await page.mouse.move(bounds.x + bounds.width / 2 + 80, bounds.y + 40);
  await page.mouse.up();
  await expect.poll(() => sidebar.evaluate(element => element.getBoundingClientRect().width))
    .toBeGreaterThan(initialWidth);
  await expect(page.locator('.community-chat-area')).toBeVisible();
  const targetRow = page.locator('.community-user-item').filter({ hasText: targetUsername });
  await targetRow.hover();
  const directMessageButton = targetRow.locator('button[title="Send direct message"]');
  const inviteButton = targetRow.locator('button[title="Invite to game"]');
  await expect(directMessageButton).toBeVisible();
  await expect(directMessageButton).toBeEnabled();
  await expect(inviteButton).toBeVisible();
  await expect(inviteButton).toBeEnabled();

  await resizer.focus();
  await page.keyboard.press('Home');
  await expect(resizer).toHaveAttribute('aria-valuenow', '130');
  await page.keyboard.press('End');
  await expect.poll(async () => Number(await resizer.getAttribute('aria-valuenow')))
    .toBeGreaterThan(130);
  await page.close();
});

test('community refresh button updates player statuses', async ({ browser, request }) => {
  const username = `refresh_user_${randomUUID().slice(0, 8)}`;
  const targetUsername = `refresh_target_${randomUUID().slice(0, 8)}`;
  await registerUser(request, username, `${username}@example.test`);
  await registerUser(request, targetUsername, `${targetUsername}@example.test`);
  const token = await loginUser(request, username);

  const page = await browser.newPage();
  await page.addInitScript(({ authToken, currentUser }) => {
    localStorage.setItem('authToken', authToken);
    localStorage.setItem('currentUser', currentUser);
  }, { authToken: token, currentUser: username });
  await page.goto('/');
  const goToGame = page.getByRole('button', { name: 'Go to Game' });
  if (await goToGame.isVisible().catch(() => false)) await goToGame.click();
  await page.getByRole('button', { name: /Community/ }).click();

  await page.route('**/community/online-users', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      success: true,
      users: [{ username: targetUsername, activity: 'offline' }]
    })
  }));
  const refreshResponse = page.waitForResponse(response =>
    new URL(response.url()).pathname === '/community/online-users'
  );
  await page.getByRole('button', { name: 'Refresh', exact: true }).click();
  expect((await refreshResponse).ok()).toBeTruthy();
  await expect(page.locator('#community-status-dot')).toHaveText('0 online, 1 offline');
  const targetRow = page.locator('.community-user-item').filter({ hasText: targetUsername });
  await expect(targetRow.locator('.cu-offline')).toBeVisible();
  await page.close();
});

test('Community invite preview displays inert email action buttons', async ({ browser, request }) => {
  const suffix = randomUUID().slice(0, 8);
  const inviter = `preview_inviter_${suffix}`;
  const recipient = `preview_recipient_${suffix}`;
  await registerUser(request, inviter, `${inviter}@example.test`);
  await registerUser(request, recipient, `${recipient}@example.test`);
  const inviterToken = await loginUser(request, inviter);

  const page = await browser.newPage();
  await page.addInitScript(({ token, username }) => {
    localStorage.setItem('authToken', token);
    localStorage.setItem('currentUser', username);
  }, { token: inviterToken, username: inviter });
  await page.goto('/');
  const goToGame = page.getByRole('button', { name: 'Go to Game' });
  if (await goToGame.isVisible().catch(() => false)) await goToGame.click();
  await page.getByRole('button', { name: /Community/ }).click();

  const playerRow = page.locator('.community-user-item').filter({ hasText: recipient });
  await expect(playerRow).toBeVisible();
  await playerRow.hover();
  const inviteButton = playerRow.locator(`button[title="Invite to game"][data-recipient="${recipient}"]`);
  await expect(inviteButton).toBeVisible();
  await inviteButton.click();

  const emailPreview = page.frameLocator('#invite-preview-email');
  await expect(emailPreview.getByRole('link', { name: 'Accept invitation' })).toHaveAttribute('href', '#');
  await expect(emailPreview.getByRole('link', { name: 'Decline' })).toHaveAttribute('href', '#');
  await expect(page.locator('#invite-preview-send')).toBeEnabled();
  await expect(page.locator('#invite-preview-email')).toHaveAttribute('sandbox', '');
  await page.close();
});

test('offline invitation, playable game, and completed-game review', async ({ browser, request }) => {
  const suffix = randomUUID().slice(0, 8);
  const inviter = `email_inviter_${suffix}`;
  const recipient = `email_recipient_${suffix}`;
  const outsider = `email_outsider_${suffix}`;
  const inviterEmail = `${inviter}@example.test`;
  const recipientEmail = `${recipient}@example.test`;
  await registerUser(request, inviter, inviterEmail);
  await registerUser(request, recipient, recipientEmail);
  await registerUser(request, outsider, `${outsider}@example.test`);
  const inviterToken = await loginUser(request, inviter);
  const outsiderToken = await loginUser(request, outsider);

  const inviteResponse = await request.post(`${appBaseUrl}/community/game-invite`, {
    headers: { Authorization: `Bearer ${inviterToken}` },
    data: { recipient }
  });
  expect(inviteResponse.ok()).toBeTruthy();
  expect((await inviteResponse.json()).emailed).toBeTruthy();

  const invitation = await waitForMessage(request, recipientEmail, `Chess invitation from ${inviter}`);
  expect(invitation.HTML).toContain('Accept invitation');
  expect(invitation.HTML).toContain('>Decline</a>');
  const acceptHref = invitation.HTML.match(/href="([^"]+decision=accept)"/);
  const declineHref = invitation.HTML.match(/href="([^"]+decision=decline)"/);
  expect(acceptHref).toBeTruthy();
  expect(declineHref).toBeTruthy();
  const acceptUrl = acceptHref[1].replaceAll('&amp;', '&');
  const declineUrl = declineHref[1].replaceAll('&amp;', '&');

  const declinePage = await browser.newPage();
  await declinePage.goto(declineUrl);
  await expect(declinePage.locator('#opening-options')).toBeHidden();
  await expect(declinePage.locator('#accept-invitation')).toBeHidden();
  await expect(declinePage.getByRole('button', { name: 'Confirm decline' })).toBeVisible();
  await declinePage.close();

  const recipientPage = await browser.newPage();
  await recipientPage.goto(acceptUrl);
  await expect(recipientPage.locator('#response')).toBeVisible();
  await recipientPage.getByRole('button', { name: 'Accept invitation' }).click();
  await expect(recipientPage.locator('#intro')).toHaveText('You accepted this invitation.');
  await recipientPage.getByRole('link', { name: 'View game board' }).click();
  await expect(recipientPage).toHaveURL(/email-game\.html\?game_id=\d+/);
  const gameId = new URL(recipientPage.url()).searchParams.get('game_id');
  const recipientToken = await loginUser(request, recipient);

  await recipientPage.getByLabel('Username').fill(recipient);
  await recipientPage.getByLabel('Password').fill(testPassword);
  await recipientPage.getByRole('button', { name: 'Sign in' }).click();
  await expect(recipientPage.locator('#turn')).toHaveText(`White to move (${inviter})`);
  await expectTurnSideAtBottom(recipientPage, 'White');
  await recipientPage.getByRole('button', { name: `Sign in as White (${inviter})` }).click();
  await expect(recipientPage.locator('#game')).toBeHidden();
  await recipientPage.getByLabel('Username').fill(inviter);
  await recipientPage.getByLabel('Password').fill(testPassword);
  await recipientPage.getByRole('button', { name: 'Sign in' }).click();
  await expect(recipientPage.locator('#turn')).toHaveText('Your turn (White)');
  await recipientPage.getByRole('button', { name: 'Switch player' }).click();
  await recipientPage.getByLabel('Username').fill(recipient);
  await recipientPage.getByLabel('Password').fill(testPassword);
  await recipientPage.getByRole('button', { name: 'Sign in' }).click();
  await expect(recipientPage.locator('#turn')).toHaveText(`White to move (${inviter})`);

  const outsiderResponse = await request.get(`${appBaseUrl}/community/email-games/${gameId}`, {
    headers: { Authorization: `Bearer ${outsiderToken}` }
  });
  expect(outsiderResponse.status()).toBe(404);

  const inviterPage = await openGamePage(browser, gameId, inviter, request);
  await expect(inviterPage.locator('#turn')).toHaveText('Your turn (White)');
  await expectTurnSideAtBottom(inviterPage, 'White');

  await movePiece(inviterPage, 'e2', 'e5');
  await expect(inviterPage.locator('#feedback')).toContainText('not legal');
  await expect(inviterPage.locator('#turn')).toHaveText('Your turn (White)');

  await movePiece(inviterPage, 'e2', 'e4');
  await expect(inviterPage.locator('#turn')).toHaveText(`Black to move (${recipient})`);
  await expectTurnSideAtBottom(inviterPage, 'Black');
  const turnEmail = await waitForMessage(request, recipientEmail, `Your turn in a chess game with ${inviter}`);
  expect(turnEmail.Text).toContain('Next move: Black.');

  const staleMove = await request.post(`${appBaseUrl}/community/email-games/${gameId}/moves`, {
    headers: { Authorization: `Bearer ${recipientToken}` },
    data: { move: 'e7e5', expected_version: 0 }
  });
  expect(staleMove.status()).toBe(409);

  await recipientPage.getByRole('button', { name: 'Refresh board' }).click();
  await expect(recipientPage.locator('#turn')).toHaveText('Your turn (Black)');
  await expectTurnSideAtBottom(recipientPage, 'Black');
  await movePiece(recipientPage, 'e7', 'e5');
  await expect(recipientPage.locator('#turn')).toHaveText(`White to move (${inviter})`);
  await expectTurnSideAtBottom(recipientPage, 'White');
  await inviterPage.reload();
  await expect(inviterPage.locator('#turn')).toHaveText('Your turn (White)');
  await expectTurnSideAtBottom(inviterPage, 'White');

  inviterPage.once('dialog', dialog => dialog.accept());
  await inviterPage.getByRole('button', { name: 'Resign' }).click();
  await expect(inviterPage.locator('#game-result')).toContainText('resignation');
  await expect(inviterPage.getByRole('button', { name: 'Previous position' })).toBeVisible();
  await expect(inviterPage.getByRole('button', { name: 'Download PGN' })).toBeVisible();

  await recipientPage.close();
  await inviterPage.close();
});