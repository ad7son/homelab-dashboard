import { useLayoutEffect } from 'react';
import { useLocation } from 'react-router-dom';

// 僅在本次頁面生命週期中保存位置，不寫入瀏覽器永久儲存。
const positions = new Map<string, number>();

/**
 * 外殼捲動的是 main 而非 window，因此自行記住每個頁面的內容位置。
 * 總覽需等資料載入、內容高度恢復後才還原，避免被載入畫面的高度截斷。
 */
export function usePageScrollPosition(ready = true) {
  const { pathname } = useLocation();
  useLayoutEffect(() => {
    if (!ready) return;
    const main = document.querySelector<HTMLElement>('main.app-main');
    if (!main) return;
    main.scrollTop = positions.get(pathname) ?? 0;
    const save = () => positions.set(pathname, main.scrollTop);
    main.addEventListener('scroll', save, { passive: true });
    return () => main.removeEventListener('scroll', save);
  }, [ready, pathname]);
}
