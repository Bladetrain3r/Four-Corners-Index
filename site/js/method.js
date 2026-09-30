import { el, getText, fail, $ } from "./util.js";
import { initPage } from "./layout.js";

const { main, error } = await initPage("method");
$("#loading")?.remove();
if (error) fail(main, error);
else {
  try {
    // The fragment is generated from METHOD.md by pipeline.publish, which escapes all text; it is our own file, not user input.
    const host = el("div", { id: "method" });
    host.innerHTML = await getText("data/method.html");
    main.querySelector("h1")?.remove();
    main.append(el("p", { class: "lede" }, "This is the method as frozen in the repository (METHOD.md). Changes are new versions with a dated entry; earlier versions stay in git history."), host);
  } catch (e) { fail(main, e); }
}
