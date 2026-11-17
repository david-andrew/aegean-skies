// One browser on the test phone at a time, and the DevTools connection to that one. Chrome, Chrome
// Beta and Chromium all offer the same DevTools socket name (chrome_devtools_remote), so one left
// running in the background (a session's Chromium, say) can answer the tools instead of the browser
// they asked for. The phone tools call claimBrowser before starting theirs and checkBrowser once
// connected; the version goes into their results, so a measurement says which browser it was.
import {execFileSync} from 'node:child_process';

export const PACKAGES = {chrome: 'com.android.chrome', beta: 'com.chrome.beta', chromium: 'org.chromium.chrome'};
const adb = (...a) => execFileSync('adb', a, {encoding: 'utf8'}).trim();
const tryAdb = (...a) => { try { return adb(...a); } catch { return ''; } };

// stop the other browsers, drop this tool's old port forward; {package, version} of the one asked for
export const claimBrowser = (browser, port) => {
  const want = PACKAGES[browser];
  const stopped = [];
  for (const [name, pkg] of Object.entries(PACKAGES)) {
    if (pkg === want || !tryAdb('shell', 'pidof', pkg)) continue;
    tryAdb('shell', 'am', 'force-stop', pkg);
    stopped.push(name);
  }
  tryAdb('forward', '--remove', `tcp:${port}`);
  if (stopped.length) console.error(`phone: stopped ${stopped.join(', ')}, which would have held the DevTools socket`);
  const version = tryAdb('shell', 'dumpsys', 'package', want).match(/versionName=(\S+)/)?.[1] ?? '?';
  return {package: want, version};
};

// (once forwarded) the browser answering DevTools; an error if it is another app's
export const checkBrowser = async (port, browser) => {
  const v = await (await fetch(`http://localhost:${port}/json/version`)).json();
  const pkg = v['Android-Package'];
  if (pkg && pkg !== PACKAGES[browser]) throw new Error(`DevTools on the phone is ${pkg}, not ${PACKAGES[browser]}`);
  return v.Browser ?? '?';
};
