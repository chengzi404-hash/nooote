import { parser as javascript } from "@lezer/javascript";
import { parser as python } from "@lezer/python";
import { parser as cpp } from "@lezer/cpp";
import { parser as rust } from "@lezer/rust";
import { parser as html } from "@lezer/html";
import { parser as css } from "@lezer/css";
import { parser as json } from "@lezer/json";
import { parser as java } from "@lezer/java";
import { parser as php } from "@lezer/php";
import { parser as go } from "@lezer/go";
import { parser as yaml } from "@lezer/yaml";

export const parsers = {
  javascript,
  python,
  cpp,
  rust,
  html,
  css,
  json,
  java,
  php,
  go,
  yaml,
};
