# sources/yozai/ — Yozai（悠哉字体）

CJK 伴生字体 `ComicMathMono CJK` 的汉字/假名来源。

| 本仓库文件 | 上游 face | 版本 | 发布日期 | SHA-256 |
|---|---|---|---|---|
| `Yozai-Medium.ttf` | Yozai Medium | 0.868 | 2025-09-12 | `05f50f252b45197d0d6148a4abc3e37c7cd4cfdf03c955b57c25d53d924f835f` |
| `Yozai-Bold.ttf` | Yozai Bold | 0.850 | 2020-10-01 | `5c9eee84d1f6870379b552c97317f3d6a9c499f4c77a82704c3263870fe1ab01` |

- 上游：<https://github.com/lxgw/yozai-font>
- 上游发布：<https://github.com/lxgw/yozai-font/releases>
  - `Yozai-Medium.ttf`：`v0.868`
  - `Yozai-Bold.ttf`：`v0.850`（0.860 起上游取消 Bold；为了粗体保留此旧版）
- 原始字体：Y.OzFont by Y.OzVox — <http://yozvox.web.fc2.com>
- 许可：SIL Open Font License 1.1，见 [`LICENSE.txt`](LICENSE.txt)
- **保留字体名（Reserved Font Names）**：`Yozai`、`悠哉`、`悠哉字体`，以及 Y.OzFont 的 `Y.Oz` / `YOz`
  - 因此本项目的衍生字体 **font family / full name / PostScript name 不使用这些名字**；
  - 只在 `README` / `NOTICE` / name table 的 description 中作为来源说明出现。

## 为什么 Medium 做 Regular、0.850 Bold 做 Bold

- Yozai 0.868 只有 Light / Regular / Medium 三个字重，Medium 的视觉重量最接近 ComicMathMono Regular。
- 0.868 没有 Bold；0.850 是最后一个带真 Bold 的版本。
- 0.850 Bold 对《通用规范汉字表》8,105 字、GB2312、JIS X 0208 都是 100% 覆盖；
  缺失的 3,363 个 URO 字在 8,105 之外，粗体遇到时会回退到 Medium 或 Jigmo。

## 只取 CJK

`tools/make_cjk_companion.py` 只保留 **EAW = W/F 的 CJK 相关码点**，不引入 Yozai 的比例拉丁、
ASCII 标点、希腊/西里尔/IPA、组合符、制表符等。所有保留字形统一到 advance **1100**，
所以伴生字体是真正等宽的。

## 重新获取

```bash
curl -fLo sources/yozai/Yozai-Medium.ttf \
  https://github.com/lxgw/yozai-font/releases/download/v0.868/Yozai-Medium.ttf
curl -fLo sources/yozai/Yozai-Bold.ttf \
  https://github.com/lxgw/yozai-font/releases/download/v0.850/Yozai-Bold.ttf
```

下载后可用上面的 SHA-256 校验。
