import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";

const heroImage =
  "https://images.unsplash.com/photo-1493794179168-82ca7cb00437?crop=entropy&cs=tinysrgb&fit=crop&fm=jpg&q=85&w=1200";

type IconProps = {
  children: ReactNode;
  className?: string;
};

function Icon({ children, className = "h-5 w-5" }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      {children}
    </svg>
  );
}

const sources = [
  {
    id: "tacc",
    name: "ТАСС",
    platform: "site",
    editorial: "ТАСС",
    url: "https://www.tacc.ru/",
    badge: "T",
    badgeClass: "bg-[#127c32]",
    time: "8 минут назад",
    ageMinutes: 12,
    title: "Движение на нескольких улицах в центре Москвы временно ограничат",
    excerpt:
      "Изменения связаны с проведением городского мероприятия. Ограничения будут действовать в течение выходных.",
    match: 90,
  },
  {
    id: "rbc",
    name: "РБК",
    platform: "site",
    editorial: "РБК",
    url: "https://www.rbc.ru/",
    badge: "Р",
    badgeClass: "bg-[#123c32]",
    time: "12 минут назад",
    ageMinutes: 12,
    title: "В центре Москвы изменится схема движения в эти выходные",
    excerpt:
      "Временные ограничения начнут действовать в субботу утром. Водителям рекомендуют заранее планировать маршрут.",
    match: 96,
  },
  {
    id: "kommersant",
    name: "Коммерсантъ",
    platform: "site",
    editorial: "Коммерсантъ",
    url: "https://www.kommersant.ru/",
    badge: "К",
    badgeClass: "bg-[#171717]",
    time: "28 минут назад",
    ageMinutes: 28,
    title: "Столичный транспорт изменит маршруты на время городского события",
    excerpt:
      "Часть улиц в центре будет закрыта для автомобилей. Общественный транспорт продолжит работу по изменённой схеме.",
    match: 91,
  },
  {
    id: "vedomosti",
    name: "Ведомости",
    platform: "site",
    editorial: "Ведомости",
    url: "https://www.vedomosti.ru/",
    badge: "В",
    badgeClass: "bg-[#e9dac2] text-[#1b1b1b]",
    time: "43 минуты назад",
    ageMinutes: 43,
    title: "Власти предупредили об ограничениях движения в центре столицы",
    excerpt:
      "Ограничения затронут несколько центральных улиц и будут сняты после завершения мероприятия.",
    match: 87,
  },
];

const examples = [
  "В центре Москвы перекроют улицы",
  "ЦБ сохранил ключевую ставку",
  "Открылась новая станция метро",
];

// === Период: вместо «С» / «До» по времени ===
type PeriodKey = "all" | "1d" | "3d" | "7d" | "14d" | "30d";

const PERIOD_OPTIONS: Array<{ key: PeriodKey; label: string; days?: number }> = [
  { key: "all", label: "За всё время" },
  { key: "1d", label: "До 1 дня", days: 1 },
  { key: "3d", label: "До 3 дней", days: 3 },
  { key: "7d", label: "До 7 дней", days: 7 },
  { key: "14d", label: "До 14 дней", days: 14 },
  { key: "30d", label: "До 30 дней", days: 30 },
];

const PERIOD_LABEL_BY_KEY: Record<PeriodKey, string> = PERIOD_OPTIONS.reduce(
  (acc, item) => {
    acc[item.key] = item.label;
    return acc;
  },
  {} as Record<PeriodKey, string>,
);

const PERIOD_DAYS_BY_KEY: Record<PeriodKey, number | undefined> =
  PERIOD_OPTIONS.reduce(
    (acc, item) => {
      acc[item.key] = item.days;
      return acc;
    },
    {} as Record<PeriodKey, number | undefined>,
  );

type RawRow = {
  editorial: string;
  site?: string;
  tg?: string;
  vk?: string;
  ok?: string;
  dzen?: string;
  max?: string;
};

const rawRows: RawRow[] = [
  { editorial: "Авангард", site: "https://avangardkray.ru/", tg: "https://t.me/avangard_online", vk: "https://vk.com/avangard_online", ok: "https://ok.ru/group/56158715707477", max: "https://max.ru/id2421000338_gos" },
  { editorial: "Ангарская правда", site: "http://angarka.info/", tg: "https://t.me/angarka2022", vk: "https://vk.com/angarkainfo", ok: "https://ok.ru/angarskaya.pravda", dzen: "https://dzen.ru/id/611c742476e1862f7f85ab3a", max: "https://max.ru/id2407004884_gos" },
  { editorial: "Ангарский рабочий", site: "http://angarochka.ru", tg: "https://t.me/angarochka1", vk: "https://vk.com/angarochka24", ok: "https://ok.ru/group/53090704425047", dzen: "https://dzen.ru/id/66238cd4e69dcf3927ea044e", max: "https://max.ru/id2426000229_gos" },
  { editorial: "Ачинская газета", site: "http://pv-press.ru", tg: "https://t.me/ach_gzt24", vk: "https://vk.com/ach_gzt24", ok: "https://ok.ru/achgzt24", max: "https://max.ru/id2443046745_gos" },
  { editorial: "Вести", site: "www.vesti-uluy.ru", tg: "https://t.me/vestiului", vk: "https://vk.com/vesti_uluy", ok: "https://ok.ru/vesti.bolshoyuluy", max: "https://max.ru/id2409002339_gos" },
  { editorial: "Власть труда", site: "www.vtruda.ru", tg: "https://t.me/vtruda", vk: "http://vk.com/v_truda", ok: "https://ok.ru/vlasttruda", dzen: "https://dzen.ru/vtruda", max: "https://max.ru/ch_572953297985" },
  { editorial: "Вместе с Вами", site: "gazeta-vmeste.ru", tg: "https://t.me/vsv_gazeta", vk: "https://vk.com/vmeste_svami", ok: "https://ok.ru/gazetavmeste0", dzen: "https://dzen.ru/vsv_gazeta", max: "https://max.ru/id2430003568_gos" },
  { editorial: "Вперед", site: "www.vpered24.ru", tg: "https://t.me/vpered24", vk: "https://vk.com/vpered24/", ok: "https://ok.ru/vpered24/", max: "https://max.ru/id2440000710_gos" },
  { editorial: "Голос времени", site: "http://голосвремени.рф/", tg: "https://t.me/golosvremeni", vk: "https://vk.com/golos_vremeni", ok: "http://ok.ru/golosvreme", dzen: "https://dzen.ru/golos_vremeni", max: "https://max.ru/golosvremeni" },
  { editorial: "Голос Тюхтета", site: "http://golos-tuhteta.ru/", tg: "https://t.me/gazetagolos", vk: "https://vk.com/public184237411", ok: "https://ok.ru/group/55631355445470", max: "https://max.ru/id2438000061_gos" },
  { editorial: "Грани", site: "www.graninow.ru", tg: "https://t.me/gazetagrani", vk: "https://vk.com/club68905670", ok: "http://ok.ru/group/54673466654744", dzen: "https://dzen.ru/graninovoselovo", max: "https://max.ru/id2429001693_gos" },
  { editorial: "Дзержинец", site: "www.dzerzhinskoe.ru", tg: "https://t.me/dzerzhinskoe", vk: "https://vk.com/tarai24", ok: "http://ok.ru/dzerzhinets/topics", dzen: "https://dzen.ru/id/6638985311689f03b418f815", max: "https://max.ru/id2410002213_gos" },
  { editorial: "Емельяновские веси", site: "https://emelyanovskievesi.ru/", tg: "https://t.me/vesi1936", vk: "https://vk.com/emel_vesy", ok: "https://ok.ru/yemelyano", dzen: "https://dzen.ru/id/625047352c36a860c17f3d0e", max: "https://max.ru/id2411003530_gos" },
  { editorial: "Енисей", site: "https://www.enisey.tv", tg: "https://t.me/eniseytv", vk: "http://vk.com/eniseytvchannel", ok: "http://www.ok.ru/eniseytv/", dzen: "https://dzen.ru/enisey", max: "https://max.ru/eniseytv" },
  { editorial: "Енисейская правда", site: "http://енисейская-правда.рф", tg: "https://t.me/enpravda", vk: "https://vk.com/club118938740", ok: "http://ok.ru/yeniseyska", dzen: "https://dzen.ru/eniseyka", max: "https://max.ru/yeniseykasmi" },
  { editorial: "Заполярье", site: "https://severokrai.ru/", tg: "https://t.me/severokrai", vk: "https://vk.com/severokrai", max: "https://max.ru/join/VHhreMro-NbLWtF3KmeP5tF39hkcZTRlyR5AZw1ryG8" },
  { editorial: "Заря", site: "https://gazetazaria.ru/", tg: "https://t.me/zaria1935", vk: "https://vk.com/id586913986", ok: "http://ok.ru/profile/583268521789", max: "https://max.ru/id2431000295_gos" },
  { editorial: "Заря Енисея", site: "https://zaren.ru", tg: "https://t.me/zaryaeniseya", vk: "https://vk.com/zaryaeniseya", ok: "https://ok.ru/zaryaeniseya", max: "https://max.ru/id2454001922_gos" },
  { editorial: "Земля Боготольская", site: "https://zemlyabogotolskaya.ru/", tg: "https://t.me/gazetazb", vk: "https://vk.com/club107483759", ok: "http://ok.ru/gazetazb", max: "https://max.ru/id2444000172_gos" },
  { editorial: "Знамя труда", site: "http://ztgazeta.ru/", tg: "https://t.me/znamatruda", vk: "https://vk.com/public216447924", ok: "https://ok.ru/profile/587195283766", dzen: "https://dzen.ru/id/652f341e6bbf9502d046d110", max: "https://max.ru/id2419004279_gos" },
  { editorial: "Идринский вестник", site: "http://idr-vestnik.ru", tg: "https://t.me/IdrinskiiVestnik", vk: "https://vk.com/id566679836", ok: "https://ok.ru/profile/570973925221", dzen: "https://dzen.ru/idrinskiivestnik", max: "https://max.ru/id2414000739_gos" },
  { editorial: "Иланские вести", site: "ilanskievesti.ru", tg: "https://t.me/ilanskievesti", vk: "http://vk.com/club62778092", ok: "http://www.ok.ru/ilanskievesti", dzen: "https://dzen.ru/id/622eaa59522f83459270cce0?share_to=link", max: "https://max.ru/id2415000989_gos" },
  { editorial: "Ирбейская правда", site: "http://irbeika.ru", tg: "https://t.me/irbeika", vk: "http://vk.com/club68657817", ok: "http://ok.ru/group/56957409427490", dzen: "https://dzen.ru/irbeika124", max: "https://max.ru/id2416000340_gos" },
  { editorial: "Канские ведомости", site: "www.kvgazeta.ru", tg: "https://t.me/kvgazetaRU", vk: "http://vk.com/club48293807", ok: "http://ok.ru/kanskieve", dzen: "https://dzen.ru/kvgazetaru", max: "https://max.ru/kvgazeta" },
  { editorial: "Красное знамя", site: "https://krasnoeznamia.ru/", tg: "https://t.me/krasnoeznamia", vk: "http://vk.com/club59474892", ok: "http://ok.ru/group/53139179110605", max: "https://max.ru/id2401003394_gos" },
  { editorial: "Ленинская искра", site: "https://ленинская.рф/", tg: "https://t.me/liskrashush", vk: "https://vk.com/club29585514", ok: "https://www.ok.ru/group/58383169421370", max: "https://max.ru/id2442002375_gos" },
  { editorial: "Манская жизнь", site: "http://mananews.ru", tg: "https://t.me/manskayagazeta", vk: "https://vk.com/public157780119", ok: "http://ok.ru/profile/572824539651", max: "https://max.ru/id2424002830_gos" },
  { editorial: "Маяк Севера", site: "http://mayaksevera.ru", tg: "https://t.me/mayaksevera", vk: "https://vk.com/mayaksevera", ok: "https://ok.ru/group/53477627068608", max: "https://max.ru/id2437003180_gos2" },
  { editorial: "Наш Красноярский край", site: "http://gnkk.ru", tg: "https://t.me/gazetankk", vk: "http://vk.com/gazeta_nkk", ok: "https://ok.ru/group/53982036820182", max: "https://max.ru/gazeta_nkk" },
  { editorial: "Нива", site: "https://газетанива.рф/", tg: "https://t.me/ermniva", vk: "https://vk.com/ermniva", ok: "https://ok.ru/profile/585208252087", dzen: "https://dzen.ru/ermniva", max: "https://max.ru/id2413007756_gos" },
  { editorial: "Новая жизнь", site: "http://новаяжизнь-казачинское.рф", tg: "https://t.me/kaznewlife", vk: "https://vk.com/id407544670", ok: "https://www.ok.ru/profile/589688298030", max: "https://max.ru/id2417004192_gos" },
  { editorial: "Новое время", site: "http://новоевремя.com/", tg: "https://t.me/novtime", vk: "https://vk.com/nv1932", ok: "https://ok.ru/rayonnayag", dzen: "https://dzen.ru/id/6415cf30811aa230990e2ff5", max: "https://max.ru/id2408000593_gos" },
  { editorial: "Новый путь", site: "газета-новый-путь.рф", tg: "https://t.me/Nova_put", vk: "https://vk.com/club122303759", ok: "http://ok.ru/novypu", max: "https://max.ru/id2405000274_gos" },
  { editorial: "Огни Енисея", site: "http://дивногорск-ое.рф/", tg: "https://t.me/OgniEniseya_gazeta", vk: "https://vk.com/ognieniseya", ok: "https://ok.ru/ogniyeniseya", dzen: "https://dzen.ru/ognieniseya", max: "https://max.ru/ognieniseya" },
  { editorial: "Огни Сибири", site: "огни-сибири.рф", tg: "https://t.me/ognisibiri_news", vk: "https://vk.com/public155142744", ok: "https://www.ok.ru/group/53989872894062", dzen: "https://dzen.ru/id/66a8897d11558b714cdf369c", max: "https://max.ru/id2459000707_gos" },
  { editorial: "Победа", site: "www.pobeda24.ru", tg: "https://t.me/gazetapobeda24in", vk: "https://vk.com/public112415360", ok: "http://ok.ru/profile/576509868461/statuses", dzen: "https://dzen.ru/id/63896df762b4224b0e60ce81", max: "https://max.ru/id2428000739_gos" },
  { editorial: "Пригород", site: "http://газета-пригород.рф", tg: "https://t.me/novosti_rayona1", vk: "https://vk.com/novosti__rayona", ok: "https://ok.ru/group/70000045493072", dzen: "https://zen.yandex.ru/id/5d39ff339c944600ae8f1803", max: "https://max.ru/join/yJl0t7Yc3gfQx9gml4ZdBgloenqPMAUjhtcK7GrM0aQ" },
  { editorial: "Присаянье", site: "http://присаянье.рф/", tg: "https://t.me/prisayanie", vk: "https://vk.com/public116045812", ok: "http://ok.ru/profile/570188088274", dzen: "https://dzen.ru/pris24", max: "https://max.ru/id2433000220_gos" },
  { editorial: "Рабочий", site: "http://газетарабочий.рф", tg: "https://t.me/news_sosn", vk: "https://vk.com/gazetarabochy", ok: "https://ok.ru/group/54124910084288", dzen: "https://dzen.ru/snknews", max: "https://max.ru/gazetarabochy" },
  { editorial: "Сельская жизнь", site: "www.selo-life.ru", tg: "https://t.me/selolife24", vk: "https://vk.com/selolife", ok: "http://ok.ru/gazetase", max: "https://max.ru/id2435000634_gos" },
  { editorial: "Сельская новь", site: "www.gazeta-selnov.ru", tg: "https://t.me/balahtaSMI", vk: "http://vk.com/public100967922", ok: "https://ok.ru/group/55000637243392", dzen: "https://dzen.ru/id/659f6e6a86640b3b81aad3f0", max: "https://max.ru/id2403005894_gos" },
  { editorial: "Сельский труженик", site: "http://st.taseevo.ru", tg: "https://t.me/Stgazeta", vk: "https://vk.com/st_taseevo", ok: "https://ok.ru/group/54996913881100", max: "https://max.ru/id2436000732_gos" },
  { editorial: "Сибирский хлебороб", site: "sib-hleb.ru", tg: "https://t.me/gazetaSibhleb", vk: "https://vk.com/public127234990", ok: "http://ok.ru/gazetasibhleb", dzen: "https://dzen.ru/sibhleb1931", max: "https://max.ru/sibhleb" },
  { editorial: "Советское Приангарье", site: "http://приангарка.рф/", tg: "https://t.me/priangarka", vk: "https://vk.com/priangarka", ok: "https://ok.ru/priangarka", dzen: "https://dzen.ru/id/5f3da92824b29420ab63a41b", max: "https://max.ru/id2420002580_gos" },
  { editorial: "Советское Причулымье", site: "www.sovet-prich.ru", tg: "https://t.me/sovetprich", vk: "https://vk.com/public106803363", ok: "https://ok.ru/group/53895525630145", dzen: "https://zen.yandex.ru/id/616561bd3b86277d535566c7", max: "https://max.ru/id2456002199_gos" },
  { editorial: "Тубинские вести", site: "https://tubinka.ru/", tg: "https://t.me/tubinka_vesti", vk: "https://vk.com/tubinka", ok: "https://ok.ru/tubinka", dzen: "https://zen.yandex.ru/profile/editor/id/5d4929b59c944600ad0464d1", max: "https://max.ru/id2423000358_gos" },
  { editorial: "Эвенкийская жизнь", site: "http://эвенкийскаяжизнь.рф/", tg: "https://t.me/evenkya_life", vk: "https://vk.com/public211743390", ok: "https://ok.ru/group/70000001423620", max: "https://max.ru/join/O8T6v9GsREA9wuV1uFu8eUhDhdKJ46acBo3LJfU0lWA" },
  { editorial: "Эхо Турана", site: "exoturana.ru", tg: "https://t.me/exoturana24", vk: "https://vk.com/public217364898", ok: "https://ok.ru/profile/578365811121", dzen: "https://dzen.ru/id/679338ca67ebbf6b1f42373a", max: "https://max.ru/id2422001817_gos" },
];

type SiteCategory = "site" | "tg" | "vk" | "ok" | "dzen" | "max";

const SITE_CATEGORIES: Array<{
  key: SiteCategory;
  label: string;
  hint: string;
  color: string;
  icon: ReactNode;
}> = [
  {
    key: "site",
    label: "Сайты газет",
    hint: "Официальные сайты редакций",
    color: "#d91f2e",
    icon: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18" />
      </>
    ),
  },
  {
    key: "tg",
    label: "ТГ",
    hint: "Telegram-каналы",
    color: "#2aabee",
    icon: <path d="m21 4-4 16-6-4-4 4v-6L3 10z" />,
  },
  {
    key: "vk",
    label: "ВК",
    hint: "Сообщества ВКонтакте",
    color: "#0077ff",
    icon: <path d="M4 7h3l2 6 3-6h3l-4 10H8z" />,
  },
  {
    key: "ok",
    label: "ОК",
    hint: "Группы Одноклассники",
    color: "#ee8208",
    icon: (
      <>
        <circle cx="12" cy="9" r="3" />
        <path d="M6 20c1.5-3 4-4 6-4s4.5 1 6 4" />
      </>
    ),
  },
  {
    key: "dzen",
    label: "Дзен",
    hint: "Каналы на Дзене",
    color: "#191919",
    icon: <path d="M12 3c0 6-3 9-9 9 6 0 9 3 9 9 0-6 3-9 9-9-6 0-9-3-9-9Z" />,
  },
  {
    key: "max",
    label: "МАХ",
    hint: "Каналы в МАХ",
    color: "#7c3aed",
    icon: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="m8 15 3-6 3 6M9 13h6" />
      </>
    ),
  },
];

type SiteEntry = {
  id: string;
  category: SiteCategory;
  editorial: string;
  url: string;
  editorialColor: string;
  editorialMark: string;
};

const EDITORIAL_COLORS = [
  "#d91f2e", "#123c32", "#171717", "#9d7b4f", "#31599b", "#c93434",
  "#fc3f1d", "#4285f4", "#191919", "#e12828", "#0f766e", "#7c3aed",
];

const editorialMeta: Record<string, { color: string; mark: string }> = (() => {
  const map: Record<string, { color: string; mark: string }> = {};
  rawRows.forEach((row, index) => {
    map[row.editorial] = {
      color: EDITORIAL_COLORS[index % EDITORIAL_COLORS.length],
      mark: row.editorial.trim().charAt(0).toUpperCase(),
    };
  });
  return map;
})();

const siteEntriesByCategory: Record<SiteCategory, SiteEntry[]> = (() => {
  const result: Record<SiteCategory, SiteEntry[]> = {
    site: [],
    tg: [],
    vk: [],
    ok: [],
    dzen: [],
    max: [],
  };
  const keys: SiteCategory[] = ["site", "tg", "vk", "ok", "dzen", "max"];
  rawRows.forEach((row) => {
    keys.forEach((key) => {
      const url = row[key];
      if (!url) return;
      const meta = editorialMeta[row.editorial];
      result[key].push({
        id: `${key}::${row.editorial}`,
        category: key,
        editorial: row.editorial,
        url,
        editorialColor: meta?.color ?? "#d91f2e",
        editorialMark: meta?.mark ?? "?",
      });
    });
  });
  return result;
})();

const entriesByEditorial: Record<string, SiteEntry[]> = (() => {
  const map: Record<string, SiteEntry[]> = {};
  Object.values(siteEntriesByCategory).forEach((entries) => {
    entries.forEach((entry) => {
      if (!map[entry.editorial]) map[entry.editorial] = [];
      map[entry.editorial].push(entry);
    });
  });
  return map;
})();

const allSiteEntryIds = Object.values(siteEntriesByCategory)
  .flat()
  .map((entry) => entry.id);

type EditorialItem = {
  id: string;
  name: string;
  mark: string;
  color: string;
};

const editorialItems: EditorialItem[] = rawRows.map((row, index) => ({
  id: `editorial-${row.editorial}`,
  name: row.editorial,
  mark: row.editorial.trim().charAt(0).toUpperCase(),
  color: EDITORIAL_COLORS[index % EDITORIAL_COLORS.length],
}));

const allEditorialIds = editorialItems.map((item) => item.id);

type SourcesTab = "sites" | "editorials";
type CheckState = "none" | "partial" | "all";

function normalize(value: string) {
  return value.toLowerCase().replace(/ё/g, "е").trim();
}

function QuickSearch({
  value,
  onChange,
  placeholder,
  count,
  total,
}: {
  value: string;
  onChange: (next: string) => void;
  placeholder: string;
  count: number;
  total: number;
}) {
  return (
    <div className="mb-4">
      <div className="relative">
        <Icon className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-[#8e8680]">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-4-4" />
        </Icon>
        <input
          type="search"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          className="block w-full rounded-xl border border-[#ddd6d0] bg-white py-3 pr-10 pl-9 text-sm font-semibold text-[#2a2725] outline-none transition-colors placeholder:font-medium placeholder:text-[#aaa29c] hover:border-[#c7bdb5] focus:border-[#d91f2e]"
        />
        {value && (
          <button
            type="button"
            onClick={() => onChange("")}
            aria-label="Очистить поиск"
            className="absolute top-1/2 right-2 grid h-7 w-7 -translate-y-1/2 cursor-pointer place-items-center rounded-full text-[#8e8680] transition-colors hover:bg-[#f1ece7] hover:text-[#d91f2e]"
          >
            <Icon className="h-4 w-4">
              <path d="m6 6 12 12M18 6 6 18" />
            </Icon>
          </button>
        )}
      </div>
      {value && (
        <p className="mt-2 text-[11px] font-semibold text-[#918983]">
          Найдено: {count} из {total}
        </p>
      )}
    </div>
  );
}

function FilterSelect({
  label,
  icon,
  value,
  onChange,
  children,
}: {
  label: string;
  icon: ReactNode;
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
}) {
  return (
    <label className="group relative block min-w-0">
      <span className="mb-1.5 block text-[11px] font-extrabold tracking-[0.08em] text-[#8e8680] uppercase">
        {label}
      </span>
      <span className="relative flex items-center rounded-xl border border-[#ddd6d0] bg-white transition-colors group-hover:border-[#c7bdb5]">
        <span className="pointer-events-none absolute top-1/2 left-3.5 grid h-6 w-6 -translate-y-1/2 place-items-center rounded-md bg-[#f5f1ed] text-[#8e8680]">
          <Icon className="h-3.5 w-3.5">{icon}</Icon>
        </span>
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="w-full cursor-pointer appearance-none rounded-xl bg-transparent py-3 pr-9 pl-12 text-sm font-bold text-[#4d4844] outline-none"
        >
          {children}
        </select>
        <Icon className="pointer-events-none absolute top-1/2 right-3 h-4 w-4 -translate-y-1/2 text-[#8e8680]">
          <path d="m7 10 5 5 5-5" />
        </Icon>
      </span>
    </label>
  );
}

const FEDERAL_EDITORIALS = new Set(["ТАСС", "РБК", "Коммерсантъ", "Ведомости"]);

const ALL_SITE_ENTRIES_FLAT = Object.values(siteEntriesByCategory).flat();

export default function App() {
  const [query, setQuery] = useState("В центре Москвы перекроют улицы");
  const [searchedQuery, setSearchedQuery] = useState(query);
  const [howOpen, setHowOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [sourcesTab, setSourcesTab] = useState<SourcesTab>("sites");
  const [dateOrder, setDateOrder] = useState<"newest" | "oldest">("newest");
  const [platformFilter, setPlatformFilter] = useState<SiteCategory | "all">(
    "all",
  );
  const [editorialFilter, setEditorialFilter] = useState<string>("all");
  const [period, setPeriod] = useState<PeriodKey>("all");
  const [expandedNewsId, setExpandedNewsId] = useState<string | null>(null);

  const [siteSearch, setSiteSearch] = useState("");
  const [editorialSearch, setEditorialSearch] = useState("");
  const [faqOpen, setFaqOpen] = useState<Set<number>>(() => new Set());

  const [selectedSiteEntries, setSelectedSiteEntries] = useState(
    () => new Set(allSiteEntryIds),
  );
  const [selectedEditorials, setSelectedEditorials] = useState(
    () => new Set(allEditorialIds),
  );

  const [expandedCategories, setExpandedCategories] = useState<
    Set<SiteCategory>
  >(() => new Set());

  const syncingRef = useRef<"none" | "from-editorials" | "from-sites">("none");

  useEffect(() => {
    if (syncingRef.current === "from-sites") return;
    syncingRef.current = "from-editorials";
    setSelectedSiteEntries((currentEntries) => {
      const next = new Set(currentEntries);
      let changed = false;
      Object.entries(entriesByEditorial).forEach(
        ([editorialName, entries]) => {
          const editorialId = `editorial-${editorialName}`;
          const isEditorialSelected = selectedEditorials.has(editorialId);
          entries.forEach((entry) => {
            if (!isEditorialSelected && next.has(entry.id)) {
              next.delete(entry.id);
              changed = true;
            }
          });
        },
      );
      return changed ? next : currentEntries;
    });
    syncingRef.current = "none";
  }, [selectedEditorials]);

  const editorialCheckState = useMemo(() => {
    const map: Record<string, CheckState> = {};
    Object.entries(entriesByEditorial).forEach(([editorialName, entries]) => {
      const total = entries.length;
      let selected = 0;
      entries.forEach((entry) => {
        if (selectedSiteEntries.has(entry.id)) selected += 1;
      });
      const id = `editorial-${editorialName}`;
      map[id] =
        selected === 0 ? "none" : selected === total ? "all" : "partial";
    });
    return map;
  }, [selectedSiteEntries]);

  const normalizedSiteSearch = normalize(siteSearch);
  const filteredSiteEntriesByCategory = useMemo(() => {
    const result: Record<SiteCategory, SiteEntry[]> = {
      site: [],
      tg: [],
      vk: [],
      ok: [],
      dzen: [],
      max: [],
    };
    (Object.keys(siteEntriesByCategory) as SiteCategory[]).forEach((key) => {
      const entries = siteEntriesByCategory[key];
      result[key] = normalizedSiteSearch
        ? entries.filter(
            (entry) =>
              normalize(entry.editorial).includes(normalizedSiteSearch) ||
              normalize(entry.url).includes(normalizedSiteSearch),
          )
        : entries;
    });
    return result;
  }, [normalizedSiteSearch]);

  const visibleCategories = useMemo(
    () =>
      SITE_CATEGORIES.filter(
        (category) => filteredSiteEntriesByCategory[category.key].length > 0,
      ),
    [filteredSiteEntriesByCategory],
  );

  const matchedSiteEntriesCount = useMemo(
    () =>
      visibleCategories.reduce(
        (sum, category) =>
          sum + filteredSiteEntriesByCategory[category.key].length,
        0,
      ),
    [visibleCategories, filteredSiteEntriesByCategory],
  );

  const normalizedEditorialSearch = normalize(editorialSearch);
  const filteredEditorialItems = useMemo(
    () =>
      normalizedEditorialSearch
        ? editorialItems.filter((item) =>
            normalize(item.name).includes(normalizedEditorialSearch),
          )
        : editorialItems,
    [normalizedEditorialSearch],
  );

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (query.trim()) setSearchedQuery(query.trim());
  };

  const toggleCategoryExpanded = (key: SiteCategory) => {
    setExpandedCategories((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const toggleSiteEntry = (id: string) => {
    setSelectedSiteEntries((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleEditorial = (id: string) => {
    const editorialName = id.replace(/^editorial-/, "");
    const entries = entriesByEditorial[editorialName] ?? [];
    const state = editorialCheckState[id] ?? "none";
    const makeSelected = state !== "all";

    setSelectedEditorials((current) => {
      const next = new Set(current);
      if (makeSelected) next.add(id);
      else next.delete(id);
      return next;
    });

    syncingRef.current = "from-editorials";
    setSelectedSiteEntries((current) => {
      const next = new Set(current);
      entries.forEach((entry) => {
        if (makeSelected) next.add(entry.id);
        else next.delete(entry.id);
      });
      return next;
    });
    window.setTimeout(() => {
      syncingRef.current = "none";
    }, 0);
  };

  const setCategoryEntries = (key: SiteCategory, value: boolean) => {
    const ids = filteredSiteEntriesByCategory[key].map((entry) => entry.id);
    setSelectedSiteEntries((current) => {
      const next = new Set(current);
      if (value) ids.forEach((id) => next.add(id));
      else ids.forEach((id) => next.delete(id));
      return next;
    });
  };

  const setAllVisibleSiteEntries = (value: boolean) => {
    const ids = visibleCategories.flatMap((category) =>
      filteredSiteEntriesByCategory[category.key].map((entry) => entry.id),
    );
    setSelectedSiteEntries((current) => {
      const next = new Set(current);
      if (value) ids.forEach((id) => next.add(id));
      else ids.forEach((id) => next.delete(id));
      return next;
    });
  };

  const toggleAllEditorials = () => {
    const allSelected = filteredEditorialItems.every((item) =>
      selectedEditorials.has(item.id),
    );
    if (allSelected) {
      const ids = filteredEditorialItems.map((item) => item.id);
      setSelectedEditorials((current) => {
        const next = new Set(current);
        ids.forEach((id) => next.delete(id));
        return next;
      });
      syncingRef.current = "from-editorials";
      setSelectedSiteEntries((current) => {
        const next = new Set(current);
        filteredEditorialItems.forEach((item) => {
          (entriesByEditorial[item.name] ?? []).forEach((entry) =>
            next.delete(entry.id),
          );
        });
        return next;
      });
      window.setTimeout(() => {
        syncingRef.current = "none";
      }, 0);
    } else {
      const ids = filteredEditorialItems.map((item) => item.id);
      setSelectedEditorials((current) => {
        const next = new Set(current);
        ids.forEach((id) => next.add(id));
        return next;
      });
      syncingRef.current = "from-editorials";
      setSelectedSiteEntries((current) => {
        const next = new Set(current);
        filteredEditorialItems.forEach((item) => {
          (entriesByEditorial[item.name] ?? []).forEach((entry) =>
            next.add(entry.id),
          );
        });
        return next;
      });
      window.setTimeout(() => {
        syncingRef.current = "none";
      }, 0);
    }
  };

  const allVisibleSiteEntriesSelected =
    matchedSiteEntriesCount > 0 &&
    visibleCategories.every((category) =>
      filteredSiteEntriesByCategory[category.key].every((entry) =>
        selectedSiteEntries.has(entry.id),
      ),
    );

  const allVisibleEditorialsSelected =
    filteredEditorialItems.length > 0 &&
    filteredEditorialItems.every((item) => selectedEditorials.has(item.id));

  const allEditorialsSelected =
    selectedEditorials.size === allEditorialIds.length;
  const totalSelected = selectedSiteEntries.size + selectedEditorials.size;
  const totalAvailable = allSiteEntryIds.length + allEditorialIds.length;
  const nothingSelected = totalSelected === 0;

  const visibleSources = useMemo(() => {
    const periodDays = PERIOD_DAYS_BY_KEY[period];
    return sources
      .filter((source) => {
        if (platformFilter !== "all" && source.platform !== platformFilter) {
          return false;
        }
        if (
          editorialFilter !== "all" &&
          source.editorial !== editorialFilter
        ) {
          return false;
        }
        if (periodDays !== undefined) {
          if (source.ageMinutes > periodDays * 1440) return false;
        }
        return true;
      })
      .sort((a, b) =>
        dateOrder === "newest"
          ? a.ageMinutes - b.ageMinutes
          : b.ageMinutes - a.ageMinutes,
      );
  }, [platformFilter, editorialFilter, dateOrder, period]);

  // === Статистика источников: считается из контекста ===

  const statsEditorialsCount = useMemo(() => {
    const set = new Set(visibleSources.map((s) => s.editorial));
    return set.size;
  }, [visibleSources]);

  const statsPublicationsCount = visibleSources.length;

  const statsSpan = useMemo(() => {
    if (visibleSources.length === 0) return "—";
    const ages = visibleSources.map((s) => s.ageMinutes);
    const min = Math.min(...ages);
    const max = Math.max(...ages);
    const diff = max - min;
    if (diff < 60) return `${diff} мин`;
    const hours = Math.round(diff / 60);
    if (hours < 48) return `${hours} ч`;
    return `${Math.round(hours / 24)} дн`;
  }, [visibleSources]);

  const statsDistribution = useMemo(() => {
    if (visibleSources.length === 0) {
      return { federal: 0, regional: 0, federalPct: 0, regionalPct: 0 };
    }
    let federal = 0;
    visibleSources.forEach((s) => {
      if (FEDERAL_EDITORIALS.has(s.editorial)) federal += 1;
    });
    const regional = visibleSources.length - federal;
    const federalPct = Math.round((federal / visibleSources.length) * 100);
    const regionalPct = 100 - federalPct;
    return { federal, regional, federalPct, regionalPct };
  }, [visibleSources]);

  const statsActiveChannels = useMemo(() => {
    const activeEditorials = new Set(visibleSources.map((s) => s.editorial));
    let active = 0;
    selectedSiteEntries.forEach((id) => {
      const entry = ALL_SITE_ENTRIES_FLAT.find((e) => e.id === id);
      if (entry && activeEditorials.has(entry.editorial)) active += 1;
    });
    return active;
  }, [visibleSources, selectedSiteEntries]);

  const showFeatured =
    platformFilter === "all" &&
    editorialFilter === "all" &&
    period === "all";
  const showEmptyState = visibleSources.length === 0 && !showFeatured;

  const featuredCard = <article></article>;

  const faqItems = [
    {
      q: "Откуда берутся публикации?",
      a: "Сервис собирает материалы из редакций, отмеченных во вкладке «Источники»: официальных сайтов газет, Telegram-каналов, сообществ ВКонтакте и Одноклассников, каналов на Дзене и в МАХ. Список редакций и платформ вы задаёте сами.",
    },
    {
      q: "Что означает процент совпадения?",
      a: "Это оценка того, насколько публикация близка к вашему запросу по смыслу. Чем выше процент — тем точнее материал отвечает теме. Низкий процент не значит, что новость неверная, — просто она может освещать событие под другим углом.",
    },
    {
      q: "Почему у редакции стоит «минус» вместо галочки?",
      a: "Так отмечается частичный выбор. Если вы сняли хотя бы один канал редакции во вкладке «Сайты», в «Редакциях» у неё появится знак частичной заполненности. Один клик по чекбоксу вернёт все её каналы.",
    },
    {
      q: "Можно ли искать по конкретной редакции или платформе?",
      a: "Да. В модалке «Источники» на каждой вкладке есть поле быстрого поиска: в «Сайтах» — по названию редакции и ссылке, в «Редакциях» — по названию. Найденные элементы можно выделить или снять одной кнопкой.",
    },
    {
      q: "Что попадёт в сводку?",
      a: "Краткая сводка собирает общие факты из найденных публикаций без оценок. Рядом — статистика источников: сколько изданий написали, сколько всего публикаций и как распределились федеральные и региональные СМИ.",
    },
  ];

  const toggleFaq = (index: number) => {
    setFaqOpen((current) => {
      const next = new Set(current);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  return (
    <main className="min-h-screen bg-[#f4f1ed] text-[#181716]">
      <header className="border-b border-[#e4ded8] bg-white">
        <div className="mx-auto flex h-[76px] max-w-[1440px] items-center justify-between px-5 sm:px-8 lg:px-12">
          <a
            href="#"
            className="flex items-center gap-3"
            aria-label="Факт — главная"
          >
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#db1f2f] text-white shadow-[0_6px_18px_rgba(219,31,47,0.22)]">
              <Icon className="h-5 w-5">
                <path d="M12 3 5 7v5c0 4.6 2.9 7.3 7 9 4.1-1.7 7-4.4 7-9V7l-7-4Z" />
                <path d="m9 12 2 2 4-4" />
              </Icon>
            </span>
            <span className="text-xl font-extrabold tracking-[-0.04em]">
              ФАКТ<span className="text-[#db1f2f]">.</span>
            </span>
          </a>

          <nav className="hidden items-center gap-8 text-sm font-semibold text-[#69635f] md:flex">
            <button
              type="button"
              onClick={() => setHowOpen(true)}
              className="cursor-pointer transition-colors hover:text-[#db1f2f]"
            >
              Как это работает
            </button>
          </nav>

          <div className="flex items-center gap-2 md:hidden">
            <button
              type="button"
              onClick={() => setHowOpen(true)}
              className="grid h-10 w-10 cursor-pointer place-items-center rounded-full border border-[#e4ded8]"
              aria-label="Как это работает"
            >
              <Icon>
                <circle cx="12" cy="12" r="9" />
                <path d="M9.8 9a2.3 2.3 0 1 1 3.6 1.9c-.9.6-1.4 1.1-1.4 2.1M12 17h.01" />
              </Icon>
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1440px] lg:min-h-[calc(100vh-76px)] lg:grid-cols-[42%_58%]">
        <section
          id="how"
          className="relative overflow-hidden bg-[#d91f2e] px-5 py-14 text-white sm:px-8 sm:py-20 lg:px-12 lg:py-24 xl:px-16"
        >
          <div className="absolute -top-20 -right-32 h-96 w-96 rounded-full border border-white/15" />
          <div className="absolute -top-6 -right-16 h-64 w-64 rounded-full border border-white/15" />

          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 z-0 opacity-[0.06]"
            style={{
              backgroundImage: 'url("/torch.svg")',
              backgroundRepeat: "repeat",
              backgroundSize: "90px 144px",
              backgroundPosition: "20px 20px",
            }}
          />

          <div className="relative z-10 mx-auto max-w-xl lg:mx-0">
            <div className="mb-8 flex items-center gap-2.5 text-xs font-bold tracking-[0.16em] text-white/75 uppercase">
              <span className="h-2 w-2 rounded-full bg-white" />
              Умный поиск по новостям
            </div>
            <h1 className="max-w-lg text-[42px] leading-[1.04] font-extrabold tracking-[-0.045em] sm:text-5xl xl:text-[58px]">
              Одна новость.
              <br />
              Все точки зрения.
            </h1>
            <p className="mt-6 max-w-md text-base leading-7 text-white/75 sm:text-lg">
              Введите заголовок или опишите событие — мы найдём, что об этом
              пишут другие издания.
            </p>

            <form onSubmit={handleSubmit} className="mt-10">
              <label
                htmlFor="news-query"
                className="mb-3 block text-sm font-bold"
              >
                <p className="text-sm font-extrabold tracking-[0.12em] text-white uppercase">
                  Что искать?
                </p>
              </label>
              <div className="rounded-2xl bg-white p-2 shadow-[0_18px_45px_rgba(89,5,13,0.2)]">
                <textarea
                  id="news-query"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  rows={3}
                  placeholder="Вставьте заголовок или текст новости..."
                  className="w-full resize-none border-0 bg-transparent px-4 pt-3 text-[15px] leading-6 font-medium text-[#25211f] outline-none placeholder:text-[#aaa29c]"
                />
                <div className="flex items-center justify-end border-t border-[#eee9e5] pt-2 pr-1 pl-3">
                  <button
                    type="submit"
                    className="flex cursor-pointer items-center gap-2 rounded-xl bg-[#191716] px-5 py-3 text-sm font-bold text-white transition-all hover:bg-[#332f2c] active:scale-[0.98]"
                  >
                    Найти публикации
                    <Icon className="h-4 w-4">
                      <circle cx="11" cy="11" r="7" />
                      <path d="m20 20-4-4" />
                    </Icon>
                  </button>
                </div>
              </div>
            </form>

            {/* === Блок «ИСТОЧНИКИ» === */}
            <div className="mt-5">
              <div className="mb-2 flex items-center justify-between gap-3">
                <p className="text-sm font-extrabold tracking-[0.12em] text-white uppercase">
                  Где искать?
                </p>
                <span className="rounded-full bg-white/15 px-2.5 py-1 text-[11px] font-extrabold text-white">
                  {totalSelected}/{totalAvailable}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setSourcesOpen(true)}
                className="group flex w-full cursor-pointer items-center gap-4 rounded-2xl bg-white px-4 py-4 text-left shadow-[0_18px_45px_rgba(89,5,13,0.25)] ring-2 ring-white/30 transition-all hover:-translate-y-0.5 hover:shadow-[0_24px_55px_rgba(89,5,13,0.35)] active:scale-[0.99]"
              >
                <span className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-[#d91f2e] text-white shadow-[0_8px_20px_rgba(217,31,46,0.35)]">
                  <Icon className="h-6 w-6">
                    <circle cx="6" cy="6" r="2" />
                    <circle cx="18" cy="12" r="2" />
                    <circle cx="8" cy="18" r="2" />
                    <path d="m8 7 8 4M16 13l-6 4" />
                  </Icon>
                </span>

                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-extrabold text-[#181716]">
                    Настроить источники
                  </span>
                </span>

                <span className="flex shrink-0 items-center gap-2">
                  <span className="hidden items-center gap-1.5 sm:flex"></span>
                  <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#191716] text-white transition-transform group-hover:translate-x-0.5">
                    <Icon className="h-4 w-4">
                      <path d="m9 18 6-6-6-6" />
                    </Icon>
                  </span>
                </span>
              </button>

              <p className="mt-2 flex items-center gap-1.5 text-[11px] font-semibold text-white/75">
                <Icon className="h-3.5 w-3.5">
                  <path d="m5 12 4 4 10-10" />
                </Icon>
                По умолчанию включены все платформы и редакции
              </p>
            </div>

            <div className="mt-7">
              <p className="mb-3 text-xs font-bold text-white/55">
                Попробуйте пример:
              </p>
              <div className="flex flex-wrap gap-2">
                {examples.map((example) => (
                  <button
                    type="button"
                    key={example}
                    onClick={() => setQuery(example)}
                    className="cursor-pointer rounded-full border border-white/25 bg-white/[0.07] px-3.5 py-2 text-left text-xs font-medium text-white/85 backdrop-blur-sm transition-colors hover:bg-white hover:text-[#d91f2e]"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section
          id="sources"
          className="bg-[#f7f5f2] px-5 py-12 sm:px-8 lg:px-10 lg:py-14 xl:px-14"
        >
          <div className="mx-auto max-w-3xl">
            <div className="flex flex-col gap-5 border-b border-[#ddd7d1] pb-7">
              <div>
                <div className="mb-2 flex items-center gap-2 text-xs font-bold tracking-[0.12em] text-[#d91f2e] uppercase">
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#d91f2e] opacity-40" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-[#d91f2e]" />
                  </span>
                  {visibleSources.length > 0
                    ? `Найдено ${visibleSources.length} публикаций`
                    : "Публикаций по фильтрам не найдено"}
                </div>
                <h2 className="text-2xl font-extrabold tracking-[-0.03em] sm:text-[30px]">
                  Об этом пишут
                </h2>
              </div>

              <div className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {/* Период */}
                <FilterSelect
                  label="Период"
                  icon={
                    <>
                      <circle cx="12" cy="12" r="9" />
                      <path d="M12 7v5l3 2" />
                    </>
                  }
                  value={period}
                  onChange={(value) => setPeriod(value as PeriodKey)}
                >
                  {PERIOD_OPTIONS.map((option) => (
                    <option key={option.key} value={option.key}>
                      {option.label}
                    </option>
                  ))}
                </FilterSelect>

                {/* Сортировка по дате */}
                <FilterSelect
                  label="Сортировка по дате"
                  icon={
                    <>
                      <path d="M7 3v3M17 3v3M4 8h16M5 5h14v16H5z" />
                    </>
                  }
                  value={dateOrder}
                  onChange={(value) =>
                    setDateOrder(value as "newest" | "oldest")
                  }
                >
                  <option value="newest">Сначала новые</option>
                  <option value="oldest">Сначала старые</option>
                </FilterSelect>

                {/* Платформа */}
                <FilterSelect
                  label="Платформа"
                  icon={
                    <>
                      <circle cx="12" cy="12" r="9" />
                      <path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18" />
                    </>
                  }
                  value={platformFilter}
                  onChange={(value) =>
                    setPlatformFilter(value as SiteCategory | "all")
                  }
                >
                  <option value="all">Все платформы</option>
                  {SITE_CATEGORIES.map((category) => (
                    <option key={category.key} value={category.key}>
                      {category.label}
                    </option>
                  ))}
                </FilterSelect>

                {/* Редакция */}
                <FilterSelect
                  label="Редакция"
                  icon={
                    <>
                      <path d="M4 5h16v14H4z" />
                      <path d="M8 9h8M8 13h8M8 17h5" />
                    </>
                  }
                  value={editorialFilter}
                  onChange={setEditorialFilter}
                >
                  <option value="all">Все редакции</option>
                  {editorialItems.map((item) => (
                    <option key={item.id} value={item.name}>
                      {item.name}
                    </option>
                  ))}
                </FilterSelect>
              </div>
            </div>

            <div className="mt-6 rounded-2xl border border-[#e2dcd6] bg-white p-4 text-center shadow-[0_8px_30px_rgba(41,31,26,0.05)] sm:p-5">
              <div className="flex items-center justify-center">
                <div className="min-w-0">
                  <p className="text-xs font-bold tracking-[0.08em] text-[#9c948e] uppercase">
                    Сводка · {PERIOD_LABEL_BY_KEY[period]}
                  </p>
                  <p className="mt-1 truncate text-sm font-bold text-[#2a2725] sm:text-base">
                    «{searchedQuery}»
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-4 grid gap-4 xl:grid-cols-[1.35fr_1fr]">
              <article className="rounded-2xl border border-[#e2dcd6] bg-white p-5 sm:p-6">
                <div className="flex items-center gap-2 text-xs font-extrabold tracking-[0.1em] text-[#d91f2e] uppercase">
                  <span className="grid h-7 w-7 place-items-center rounded-lg bg-[#fff0f1]">
                    <Icon className="h-4 w-4">
                      <path d="M5 4h14v16H5zM8 8h8M8 12h8M8 16h5" />
                    </Icon>
                  </span>
                  Краткая сводка
                </div>
                <p className="mt-4 text-sm leading-6 font-medium text-[#514c48]">
                  В центре Москвы временно ограничат движение из-за городского
                  мероприятия. Перекрытия начнут действовать в субботу утром и
                  затронут несколько центральных улиц. Водителям советуют
                  заранее выбирать альтернативные маршруты.
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {["Москва", "Транспорт", "Выходные"].map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full bg-[#f5f1ed] px-3 py-1.5 text-[11px] font-bold text-[#756e68]"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </article>

              <aside className="rounded-2xl bg-[#211f1d] p-5 text-white sm:p-6">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-extrabold tracking-[0.1em] text-white/55 uppercase">
                    Статистика источников
                  </p>
                  <Icon className="h-4 w-4 text-[#ef4755]">
                    <path d="M4 19V9M10 19V5M16 19v-7M22 19H2" />
                  </Icon>
                </div>

                <p className="mt-2 text-[10px] font-semibold text-white/40">
                  {PERIOD_LABEL_BY_KEY[period]}
                  {platformFilter !== "all" &&
                    ` · ${
                      SITE_CATEGORIES.find((c) => c.key === platformFilter)
                        ?.label
                    }`}
                  {editorialFilter !== "all" && ` · ${editorialFilter}`}
                </p>

                <div className="mt-5 grid grid-cols-3 gap-3">
                  <div>
                    <p className="text-2xl font-extrabold tracking-[-0.04em]">
                      {statsEditorialsCount}
                    </p>
                    <p className="mt-1 text-[10px] leading-4 text-white/50">
                      {statsEditorialsCount === 1 ? "издание" : "изданий"}
                    </p>
                  </div>
                  <div>
                    <p className="text-2xl font-extrabold tracking-[-0.04em]">
                      {statsPublicationsCount}
                    </p>
                    <p className="mt-1 text-[10px] leading-4 text-white/50">
                      {statsPublicationsCount === 1
                        ? "публикация"
                        : "публикации"}
                    </p>
                  </div>
                  <div>
                    <p className="text-2xl font-extrabold tracking-[-0.04em]">
                      {statsSpan}
                    </p>
                    <p className="mt-1 text-[10px] leading-4 text-white/50">
                      охват
                    </p>
                  </div>
                </div>

                <div className="mt-5 border-t border-white/10 pt-4">
                  <div className="mb-2 flex justify-between text-[10px] font-bold text-white/55">
                    <span>Федеральные СМИ</span>
                    <span>{statsDistribution.federalPct}%</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                    <div
                      className="h-full rounded-full bg-[#ef4755] transition-all duration-500"
                      style={{ width: `${statsDistribution.federalPct}%` }}
                    />
                  </div>

                  <div className="mt-3 mb-2 flex justify-between text-[10px] font-bold text-white/55">
                    <span>Региональные СМИ</span>
                    <span>{statsDistribution.regionalPct}%</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                    <div
                      className="h-full rounded-full bg-white/70 transition-all duration-500"
                      style={{ width: `${statsDistribution.regionalPct}%` }}
                    />
                  </div>
                </div>
              </aside>
            </div>

            <div className="mt-5 space-y-3">
              {showFeatured && dateOrder === "newest" && featuredCard}

              {visibleSources.map((source) => {
                const isExpanded = expandedNewsId === source.id;

                return (
                  <article
                    key={source.id}
                    onClick={() =>
                      setExpandedNewsId(isExpanded ? null : source.id)
                    }
                    className="cursor-pointer rounded-2xl border border-[#e2dcd6] bg-white p-5 transition-all duration-300 hover:-translate-y-0.5 hover:border-[#d3cbc4] hover:shadow-[0_10px_30px_rgba(41,31,26,0.07)]"
                  >
                    <div className="flex items-start gap-4">
                      <span
                        className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl text-sm font-black text-white ${source.badgeClass}`}
                      >
                        {source.badge}
                      </span>

                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2 text-sm">
                            <span className="font-extrabold">{source.name}</span>
                            <span className="text-[#b5ada7]">•</span>
                            <span className="text-[#9a928c]">{source.time}</span>
                          </div>

                          <span className="rounded-full bg-[#fff0f1] px-2.5 py-1 text-[11px] font-extrabold text-[#d91f2e]">
                            {source.match}% совпадение
                          </span>
                        </div>

                        <h3 className="mt-3 leading-snug font-extrabold tracking-[-0.015em]">
                          {source.title}
                        </h3>

                        <p
                          className={`mt-2 text-sm leading-6 text-[#77706b] ${
                            isExpanded ? "" : "line-clamp-2"
                          }`}
                        >
                          {source.excerpt}
                        </p>

                        {isExpanded && (
                          <a
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(event) => event.stopPropagation()}
                            className="mt-4 inline-flex items-center gap-2 text-sm font-bold text-[#d91f2e] hover:underline"
                          >
                            Читать в источнике
                            <Icon className="h-4 w-4">
                              <path d="M7 17 17 7M8 7h9v9" />
                            </Icon>
                          </a>
                        )}
                      </div>
                    </div>
                  </article>
                );
              })}

              {showFeatured && dateOrder === "oldest" && featuredCard}

              {showEmptyState && (
                <div className="rounded-2xl border border-dashed border-[#d9d2cc] bg-white px-5 py-10 text-center">
                  <p className="text-sm font-bold text-[#514c48]">
                    По выбранным фильтрам публикаций нет
                  </p>
                  <p className="mt-1 text-xs text-[#918983]">
                    Попробуйте выбрать другой период, платформу или редакцию.
                  </p>
                </div>
              )}
            </div>

            {visibleSources.length > 0 && (
              <button
                type="button"
                className="mt-5 w-full cursor-pointer rounded-xl border border-[#d9d2cc] bg-transparent py-3.5 text-sm font-bold transition-colors hover:border-[#d91f2e] hover:bg-white hover:text-[#d91f2e]"
              >
                Показать ещё публикации
              </button>
            )}
          </div>
        </section>
      </div>

      {howOpen && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-[#181411]/55 p-0 backdrop-blur-[3px] sm:items-center sm:p-5"
          onMouseDown={() => setHowOpen(false)}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="how-title"
            onMouseDown={(event) => event.stopPropagation()}
            className="max-h-[92vh] w-full overflow-y-auto rounded-t-[28px] bg-[#f7f5f2] shadow-[0_30px_90px_rgba(23,18,15,0.3)] sm:max-w-3xl sm:rounded-[28px]"
          >
            <div className="relative overflow-hidden bg-[#d91f2e] px-5 py-7 text-white sm:px-8 sm:py-9">
              <div className="absolute -top-20 right-12 h-56 w-56 rounded-full border border-white/15" />
              <div className="absolute -top-10 right-24 h-36 w-36 rounded-full border border-white/15" />
              <button
                type="button"
                onClick={() => setHowOpen(false)}
                className="absolute top-5 right-5 z-10 grid h-10 w-10 cursor-pointer place-items-center rounded-full bg-white/15 text-white transition-colors hover:bg-white/25"
                aria-label="Закрыть"
              >
                <Icon className="h-5 w-5">
                  <path d="m6 6 12 12M18 6 6 18" />
                </Icon>
              </button>
              <div className="relative max-w-xl pr-12">
                <p className="mb-2 text-[11px] font-extrabold tracking-[0.14em] text-white/65 uppercase">
                  Быстрый старт
                </p>
                <h2
                  id="how-title"
                  className="text-3xl font-extrabold tracking-[-0.04em] sm:text-4xl"
                >
                  Как работает ФАКТ
                </h2>
                <p className="mt-3 max-w-lg text-sm leading-6 text-white/80">
                  Один запрос — и вы видите, как одну и ту же новость освещают
                  разные редакции: что общего в фактах, чем отличаются
                  формулировки и кто написал первым.
                </p>
              </div>
            </div>

            <div className="px-5 py-6 sm:px-8 sm:py-8">
              <div className="grid gap-3 sm:grid-cols-2">
                {[
                  {
                    number: "01",
                    title: "Опишите новость",
                    text: "Вставьте заголовок, ссылку или коротко опишите событие своими словами. Достаточно одной фразы — остальное сервис поймёт сам.",
                    icon: (
                      <>
                        <path d="M4 5h16v14H4z" />
                        <path d="M8 9h8M8 13h5" />
                      </>
                    ),
                  },
                  {
                    number: "02",
                    title: "Проверьте источники",
                    text: "В модалке «Источники» отметьте платформы и редакции, которым доверяете. По умолчанию включены все — можно сузить охват.",
                    icon: (
                      <>
                        <circle cx="6" cy="6" r="2" />
                        <circle cx="18" cy="12" r="2" />
                        <circle cx="8" cy="18" r="2" />
                        <path d="m8 7 8 4M16 13l-6 4" />
                      </>
                    ),
                  },
                  {
                    number: "03",
                    title: "Получите подборку",
                    text: "Сервис найдёт похожие материалы, отсортирует их по времени или по проценту совпадения и соберёт краткую сводку по общим фактам.",
                    icon: (
                      <>
                        <circle cx="11" cy="11" r="7" />
                        <path d="m20 20-4-4" />
                      </>
                    ),
                  },
                  {
                    number: "04",
                    title: "Сравните точки зрения",
                    text: "Откройте публикацию, чтобы прочитать оригинал, и сравните формулировки разных изданий. Так проще заметить акценты и расхождения.",
                    icon: (
                      <>
                        <path d="M5 4h14v16H5z" />
                        <path d="M8 9h8M8 13h8M8 17h4" />
                      </>
                    ),
                  },
                ].map((step) => (
                  <article
                    key={step.number}
                    className="relative overflow-hidden rounded-2xl border border-[#e2dcd6] bg-white p-5"
                  >
                    <span className="absolute top-3 right-4 text-4xl font-extrabold tracking-[-0.06em] text-[#eee9e5]">
                      {step.number}
                    </span>
                    <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#fff0f1] text-[#d91f2e]">
                      <Icon className="h-5 w-5">{step.icon}</Icon>
                    </span>
                    <h3 className="mt-5 text-base font-extrabold">
                      {step.title}
                    </h3>
                    <p className="mt-2 text-xs leading-5 text-[#817a74]">
                      {step.text}
                    </p>
                  </article>
                ))}
              </div>

              <div className="mt-6 rounded-2xl border border-[#e2dcd6] bg-white p-5 sm:p-6">
                <div className="flex items-center gap-2 text-xs font-extrabold tracking-[0.1em] text-[#d91f2e] uppercase">
                  <span className="grid h-7 w-7 place-items-center rounded-lg bg-[#fff0f1]">
                    <Icon className="h-4 w-4">
                      <path d="M4 19V9M10 19V5M16 19v-7M22 19H2" />
                    </Icon>
                  </span>
                  Как читать результаты
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  {[
                    {
                      title: "Процент совпадения",
                      text: "Насколько публикация близка к вашему запросу по смыслу. Чем выше — тем точнее материал отвечает теме.",
                    },
                    {
                      title: "Краткая сводка",
                      text: "Общие факты из найденных публикаций без оценок: что произошло, где и когда.",
                    },
                    {
                      title: "Статистика источников",
                      text: "Сколько изданий написали о событии, сколько всего публикаций и как распределились федеральные и региональные СМИ.",
                    },
                  ].map((item) => (
                    <div
                      key={item.title}
                      className="rounded-xl bg-[#faf8f6] p-4"
                    >
                      <p className="text-sm font-extrabold">{item.title}</p>
                      <p className="mt-1.5 text-xs leading-5 text-[#817a74]">
                        {item.text}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-4 rounded-2xl bg-[#211f1d] p-5 text-white sm:p-6">
                <p className="text-xs font-extrabold tracking-[0.1em] text-[#ef4755] uppercase">
                  Настройка источников
                </p>
                <div className="mt-3 grid gap-4 sm:grid-cols-2">
                  <div>
                    <p className="text-sm font-extrabold">Вкладка «Сайты»</p>
                    <p className="mt-1.5 text-xs leading-5 text-white/70">
                      Шесть платформ — сайты газет, ТГ, ВК, ОК, Дзен, МАХ.
                      Разверните платформу, чтобы выбрать конкретные каналы,
                      или используйте быстрый поиск по названию редакции и
                      ссылке.
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-extrabold">Вкладка «Редакции»</p>
                    <p className="mt-1.5 text-xs leading-5 text-white/70">
                      Список всех редакций. Снятие редакции автоматически
                      снимает все её каналы. Если снять часть каналов, у
                      редакции появится знак частичной заполненности.
                    </p>
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {[
                    "Быстрый поиск по названию и ссылке",
                    "Частичные галочки",
                    "Выбрать все / снять все",
                  ].map((chip) => (
                    <span
                      key={chip}
                      className="flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1.5 text-[11px] font-semibold text-white/85"
                    >
                      <span className="grid h-3.5 w-3.5 place-items-center rounded-full bg-[#d91f2e] text-white">
                        <Icon className="h-2 w-2">
                          <path d="m5 12 4 4 10-10" />
                        </Icon>
                      </span>
                      {chip}
                    </span>
                  ))}
                </div>
              </div>

              <div className="mt-6">
                <div className="mb-3 flex items-center gap-2 text-xs font-extrabold tracking-[0.1em] text-[#d91f2e] uppercase">
                  <span className="grid h-7 w-7 place-items-center rounded-lg bg-[#fff0f1]">
                    <Icon className="h-4 w-4">
                      <circle cx="12" cy="12" r="9" />
                      <path d="M9.8 9a2.3 2.3 0 1 1 3.6 1.9c-.9.6-1.4 1.1-1.4 2.1M12 17h.01" />
                    </Icon>
                  </span>
                  Частые вопросы
                </div>
                <div className="flex flex-col gap-2">
                  {faqItems.map((item, index) => {
                    const isOpen = faqOpen.has(index);
                    return (
                      <div
                        key={item.q}
                        className="overflow-hidden rounded-xl border border-[#e2dcd6] bg-white"
                      >
                        <button
                          type="button"
                          onClick={() => toggleFaq(index)}
                          className="flex w-full cursor-pointer items-center justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-[#faf8f6]"
                          aria-expanded={isOpen}
                        >
                          <span className="text-sm font-extrabold">
                            {item.q}
                          </span>
                          <Icon
                            className={`h-4 w-4 shrink-0 text-[#8e8680] transition-transform ${
                              isOpen ? "rotate-180" : ""
                            }`}
                          >
                            <path d="m7 10 5 5 5-5" />
                          </Icon>
                        </button>
                        {isOpen && (
                          <div className="border-t border-[#eee9e5] bg-[#faf8f6] px-4 py-3">
                            <p className="text-xs leading-5 text-[#6b655f]">
                              {item.a}
                            </p>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-end">
                <button
                  type="button"
                  onClick={() => {
                    setHowOpen(false);
                    setSourcesOpen(true);
                  }}
                  className="flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-[#d9d2cc] bg-white px-5 py-3 text-sm font-extrabold text-[#292522] transition-colors hover:border-[#d91f2e] hover:text-[#d91f2e]"
                >
                  <Icon className="h-4 w-4">
                    <circle cx="6" cy="6" r="2" />
                    <circle cx="18" cy="12" r="2" />
                    <circle cx="8" cy="18" r="2" />
                    <path d="m8 7 8 4M16 13l-6 4" />
                  </Icon>
                  Настроить источники
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setHowOpen(false);
                    window.setTimeout(
                      () => document.getElementById("news-query")?.focus(),
                      100,
                    );
                  }}
                  className="flex cursor-pointer items-center justify-center gap-2 rounded-xl bg-[#d91f2e] px-5 py-3 text-sm font-extrabold text-white transition-colors hover:bg-[#ef3040]"
                >
                  Попробовать сейчас
                  <Icon className="h-4 w-4">
                    <path d="m9 18 6-6-6-6" />
                  </Icon>
                </button>
              </div>
            </div>
          </section>
        </div>
      )}

      {sourcesOpen && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-[#181411]/55 p-0 backdrop-blur-[3px] sm:items-center sm:p-5"
          onMouseDown={() => setSourcesOpen(false)}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="sources-title"
            onMouseDown={(event) => event.stopPropagation()}
            className="flex max-h-[92vh] w-full flex-col overflow-hidden rounded-t-[28px] bg-[#f7f5f2] shadow-[0_30px_90px_rgba(23,18,15,0.3)] sm:max-w-3xl sm:rounded-[28px]"
          >
            <div className="flex items-start justify-between border-b border-[#e2dcd6] bg-white px-5 py-5 sm:px-7 sm:py-6">
              <div>
                <p className="mb-1.5 text-[11px] font-extrabold tracking-[0.12em] text-[#d91f2e] uppercase">
                  Настройка поиска
                </p>
                <h2
                  id="sources-title"
                  className="text-2xl font-extrabold tracking-[-0.035em]"
                >
                  Выберите источники
                </h2>
                <p className="mt-2 text-sm text-[#817a74]">
                  Воспользуйтесь быстрым поиском или разверните платформу, чтобы
                  выбрать конкретные каналы. Выбор редакции влияет на все её
                  каналы.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSourcesOpen(false)}
                className="grid h-10 w-10 shrink-0 cursor-pointer place-items-center rounded-full bg-[#f4f1ed] text-[#5f5954] transition-colors hover:bg-[#ebe5df] hover:text-[#d91f2e]"
                aria-label="Закрыть"
              >
                <Icon className="h-5 w-5">
                  <path d="m6 6 12 12M18 6 6 18" />
                </Icon>
              </button>
            </div>

            <div className="flex gap-1 border-b border-[#e2dcd6] bg-white px-5 sm:px-7">
              <button
                type="button"
                onClick={() => setSourcesTab("sites")}
                className={`-mb-px cursor-pointer border-b-2 px-4 py-3 text-sm font-extrabold transition-colors ${
                  sourcesTab === "sites"
                    ? "border-[#d91f2e] text-[#d91f2e]"
                    : "border-transparent text-[#7a736d] hover:text-[#2a2725]"
                }`}
              >
                Сайты
                <span className="ml-2 rounded-full bg-[#fff0f1] px-2 py-0.5 text-[10px] font-extrabold text-[#d91f2e]">
                  {selectedSiteEntries.size}/{allSiteEntryIds.length}
                </span>
              </button>
              <button
                type="button"
                onClick={() => setSourcesTab("editorials")}
                className={`-mb-px cursor-pointer border-b-2 px-4 py-3 text-sm font-extrabold transition-colors ${
                  sourcesTab === "editorials"
                    ? "border-[#d91f2e] text-[#d91f2e]"
                    : "border-transparent text-[#7a736d] hover:text-[#2a2725]"
                }`}
              >
                Редакции
                <span className="ml-2 rounded-full bg-[#fff0f1] px-2 py-0.5 text-[10px] font-extrabold text-[#d91f2e]">
                  {selectedEditorials.size}/{allEditorialIds.length}
                </span>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-5 sm:px-7 sm:py-6">
              {sourcesTab === "sites" && (
                <section aria-labelledby="sites-heading">
                  <QuickSearch
                    value={siteSearch}
                    onChange={setSiteSearch}
                    placeholder="Поиск по редакции или ссылке…"
                    count={matchedSiteEntriesCount}
                    total={allSiteEntryIds.length}
                  />

                  <div className="mb-3 flex items-center justify-between gap-3">
                    <div>
                      <h3
                        id="sites-heading"
                        className="flex items-center gap-2 text-sm font-extrabold tracking-[0.04em] text-[#2a2725] uppercase"
                      >
                        <Icon className="h-4 w-4 text-[#d91f2e]">
                          <circle cx="12" cy="12" r="9" />
                          <path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18" />
                        </Icon>
                        Платформы
                      </h3>
                      <p className="mt-1 text-xs text-[#918983]">
                        Выбрано {selectedSiteEntries.size} из{" "}
                        {allSiteEntryIds.length} каналов
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        setAllVisibleSiteEntries(!allVisibleSiteEntriesSelected)
                      }
                      className="cursor-pointer rounded-lg border border-[#ddd6d0] bg-white px-3 py-1.5 text-xs font-bold text-[#5f5954] transition-colors hover:border-[#d91f2e] hover:text-[#d91f2e]"
                    >
                      {allVisibleSiteEntriesSelected
                        ? siteSearch
                          ? "Снять найденные"
                          : "Снять все"
                        : siteSearch
                          ? "Выбрать найденные"
                          : "Выбрать все"}
                    </button>
                  </div>

                  {visibleCategories.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-[#d9d2cc] bg-white px-4 py-10 text-center">
                      <p className="text-sm font-bold text-[#514c48]">
                        Ничего не найдено
                      </p>
                      <p className="mt-1 text-xs text-[#918983]">
                        Попробуйте изменить запрос — например, часть названия
                        редакции или домен.
                      </p>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-2">
                      {visibleCategories.map((category) => {
                        const entries =
                          filteredSiteEntriesByCategory[category.key];
                        const selectedCount = entries.filter((entry) =>
                          selectedSiteEntries.has(entry.id),
                        ).length;
                        const isAllSelected =
                          entries.length > 0 &&
                          selectedCount === entries.length;
                        const isNoneSelected = selectedCount === 0;
                        const isExpanded = siteSearch
                          ? true
                          : expandedCategories.has(category.key);

                        return (
                          <div
                            key={category.key}
                            className="overflow-hidden rounded-xl border border-[#e2dcd6] bg-white"
                          >
                            <div
                              role="button"
                              tabIndex={0}
                              onClick={() =>
                                toggleCategoryExpanded(category.key)
                              }
                              onKeyDown={(event) => {
                                if (
                                  event.key === "Enter" ||
                                  event.key === " "
                                ) {
                                  event.preventDefault();
                                  toggleCategoryExpanded(category.key);
                                }
                              }}
                              className="flex w-full cursor-pointer items-center gap-3 px-3 py-3 text-left transition-colors hover:bg-[#faf8f6]"
                            >
                              <span
                                className="grid h-10 w-10 shrink-0 place-items-center rounded-xl text-white"
                                style={{ backgroundColor: category.color }}
                              >
                                <Icon className="h-5 w-5">
                                  {category.icon}
                                </Icon>
                              </span>

                              <span className="min-w-0 flex-1">
                                <span className="block truncate text-sm font-extrabold">
                                  {category.label}
                                </span>
                                <span className="mt-0.5 block truncate text-[11px] text-[#918983]">
                                  {selectedCount} из {entries.length} выбрано
                                  {siteSearch ? " · найдено по запросу" : ""}
                                </span>
                              </span>

                              <button
                                type="button"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  setCategoryEntries(
                                    category.key,
                                    !isAllSelected,
                                  );
                                }}
                                aria-label={
                                  isAllSelected
                                    ? `Снять все ${category.label}`
                                    : `Выбрать все ${category.label}`
                                }
                                className={`grid h-6 w-6 shrink-0 place-items-center rounded-md border transition-colors ${
                                  isAllSelected
                                    ? "border-[#d91f2e] bg-[#d91f2e] text-white"
                                    : isNoneSelected
                                      ? "border-[#c8c0b9] bg-white"
                                      : "border-[#d91f2e] bg-[#fff0f1] text-[#d91f2e]"
                                }`}
                              >
                                {isAllSelected && (
                                  <Icon className="h-3.5 w-3.5">
                                    <path d="m5 12 4 4 10-10" />
                                  </Icon>
                                )}
                                {!isAllSelected && !isNoneSelected && (
                                  <span className="h-0.5 w-3 rounded bg-[#d91f2e]" />
                                )}
                              </button>

                              <Icon
                                className={`h-4 w-4 shrink-0 text-[#8e8680] transition-transform ${
                                  isExpanded ? "rotate-180" : ""
                                }`}
                              >
                                <path d="m7 10 5 5 5-5" />
                              </Icon>
                            </div>

                            {isExpanded && (
                              <div className="border-t border-[#eee9e5] bg-[#faf8f6] px-3 py-2">
                                {entries.length === 0 ? (
                                  <p className="px-1 py-2 text-xs text-[#918983]">
                                    Нет редакций в этой категории
                                  </p>
                                ) : (
                                  <ul className="flex flex-col">
                                    {entries.map((entry) => {
                                      const isSelected =
                                        selectedSiteEntries.has(entry.id);
                                      return (
                                        <li key={entry.id}>
                                          <button
                                            type="button"
                                            onClick={() =>
                                              toggleSiteEntry(entry.id)
                                            }
                                            className="flex w-full cursor-pointer items-center gap-3 rounded-lg px-1 py-2 text-left transition-colors hover:bg-[#f1ece7]"
                                          >
                                            <span
                                              className="grid h-7 w-7 shrink-0 place-items-center rounded-md text-[11px] font-black text-white"
                                              style={{
                                                backgroundColor:
                                                  entry.editorialColor,
                                              }}
                                            >
                                              {entry.editorialMark}
                                            </span>
                                            <span className="min-w-0 flex-1">
                                              <span className="block truncate text-sm font-semibold">
                                                {entry.editorial}
                                              </span>
                                              <span className="mt-0.5 block truncate text-[11px] text-[#918983]">
                                                {entry.url}
                                              </span>
                                            </span>
                                            <span
                                              className={`grid h-5 w-5 shrink-0 place-items-center rounded-md border ${
                                                isSelected
                                                  ? "border-[#d91f2e] bg-[#d91f2e] text-white"
                                                  : "border-[#c8c0b9] bg-white"
                                              }`}
                                            >
                                              {isSelected && (
                                                <Icon className="h-3 w-3">
                                                  <path d="m5 12 4 4 10-10" />
                                                </Icon>
                                              )}
                                            </span>
                                          </button>
                                        </li>
                                      );
                                    })}
                                  </ul>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </section>
              )}

              {sourcesTab === "editorials" && (
                <section aria-labelledby="editorials-heading">
                  <QuickSearch
                    value={editorialSearch}
                    onChange={setEditorialSearch}
                    placeholder="Поиск по названию редакции…"
                    count={filteredEditorialItems.length}
                    total={allEditorialIds.length}
                  />

                  <div className="mb-3 flex items-center justify-between gap-3">
                    <div>
                      <h3
                        id="editorials-heading"
                        className="flex items-center gap-2 text-sm font-extrabold tracking-[0.04em] text-[#2a2725] uppercase"
                      >
                        <Icon className="h-4 w-4 text-[#d91f2e]">
                          <path d="M4 5h16v14H4z" />
                          <path d="M8 9h8M8 13h8M8 17h5" />
                        </Icon>
                        Редакции газет
                      </h3>
                      <p className="mt-1 text-xs text-[#918983]">
                        Выбрано {selectedEditorials.size} из{" "}
                        {allEditorialIds.length}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={toggleAllEditorials}
                      className="cursor-pointer rounded-lg border border-[#ddd6d0] bg-white px-3 py-1.5 text-xs font-bold text-[#5f5954] transition-colors hover:border-[#d91f2e] hover:text-[#d91f2e]"
                    >
                      {allVisibleEditorialsSelected
                        ? editorialSearch
                          ? "Снять найденные"
                          : "Снять все"
                        : editorialSearch
                          ? "Выбрать найденные"
                          : "Выбрать все"}
                    </button>
                  </div>

                  {filteredEditorialItems.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-[#d9d2cc] bg-white px-4 py-10 text-center">
                      <p className="text-sm font-bold text-[#514c48]">
                        Ничего не найдено
                      </p>
                      <p className="mt-1 text-xs text-[#918983]">
                        Попробуйте изменить запрос — например, часть названия
                        редакции.
                      </p>
                    </div>
                  ) : (
                    <div className="grid gap-2 sm:grid-cols-2">
                      {filteredEditorialItems.map((editorial) => {
                        const state =
                          editorialCheckState[editorial.id] ?? "none";
                        const isAll = state === "all";
                        const isPartial = state === "partial";
                        const isInEditorials = selectedEditorials.has(
                          editorial.id,
                        );
                        const visualSelected =
                          isAll || isPartial || isInEditorials;

                        return (
                          <button
                            type="button"
                            key={editorial.id}
                            onClick={() => toggleEditorial(editorial.id)}
                            className={`flex cursor-pointer items-center gap-3 rounded-xl border p-3 text-left transition-all ${
                              visualSelected
                                ? "border-[#d9d1ca] bg-white"
                                : "border-transparent bg-[#efebe7] opacity-55 hover:opacity-80"
                            }`}
                          >
                            <span
                              className="grid h-10 w-10 shrink-0 place-items-center rounded-xl text-sm font-black text-white"
                              style={{ backgroundColor: editorial.color }}
                            >
                              {editorial.mark}
                            </span>
                            <span className="min-w-0 flex-1">
                              <span className="block truncate text-sm font-extrabold">
                                {editorial.name}
                              </span>
                              <span className="mt-0.5 block truncate text-[11px] text-[#918983]">
                                {isPartial
                                  ? "Выбрана часть каналов"
                                  : "Редакция газеты"}
                              </span>
                            </span>
                            <span
                              className={`grid h-5 w-5 shrink-0 place-items-center rounded-md border ${
                                isAll
                                  ? "border-[#d91f2e] bg-[#d91f2e] text-white"
                                  : isPartial
                                    ? "border-[#d91f2e] bg-[#fff0f1] text-[#d91f2e]"
                                    : "border-[#c8c0b9] bg-white"
                              }`}
                            >
                              {isAll && (
                                <Icon className="h-3 w-3">
                                  <path d="m5 12 4 4 10-10" />
                                </Icon>
                              )}
                              {isPartial && (
                                <span className="h-0.5 w-3 rounded bg-[#d91f2e]" />
                              )}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </section>
              )}
            </div>

            <div className="flex items-center justify-between border-t border-[#e2dcd6] bg-white px-5 py-4 sm:px-7">
              <p className="text-xs font-semibold text-[#817a74]">
                Выбрано:{" "}
                <span className="font-extrabold text-[#292522]">
                  {selectedSiteEntries.size} каналов,{" "}
                  {selectedEditorials.size} редакций
                </span>
              </p>
              <button
                type="button"
                disabled={nothingSelected}
                onClick={() => setSourcesOpen(false)}
                className="cursor-pointer rounded-xl bg-[#d91f2e] px-5 py-3 text-sm font-extrabold text-white transition-colors hover:bg-[#bd1725] disabled:cursor-not-allowed disabled:opacity-40"
              >
                Применить
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}