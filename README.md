# First

微信小程序安全调试工具 — Frida + CDP，支持 macOS / Windows

## 免责声明

本工具仅供安全研究与学习使用，请勿用于未授权的目标，使用者须自行承担相关法律责任。

## 功能

- Frida 注入微信，CDP 代理桥接 Chrome DevTools
- 云函数动态捕获（Hook wx.cloud.callFunction，参数修改重放）
- wx.* API 捕获（login / request / getUserProfile 等）
- 路由枚举与导航，跳转守卫检测
- wxapkg 解密解包 + 敏感信息扫描
- MCP Server 集成（AI 辅助分析）
- 偏移量 / Skills 在线更新

## 截图
### 主页
![11071](https://s1.galgame.fun/imgb/u55/20260601_6a1d43338429a.png)
### 云函数捕获
![11069](https://s1.galgame.fun/imgb/u55/20260601_6a1d4333632a4.png)
### wx.api捕获
![11072](https://s1.galgame.fun/imgb/u55/20260601_6a1d43338219d.png)
### 反编译文件编辑搜索
![11073](https://s1.galgame.fun/imgb/u55/20260601_6a1d433372934.png)
### Frist-MCP
![11070](https://s1.galgame.fun/imgb/u55/20260601_6a1d433358324.png)
![11074](https://s1.galgame.fun/imgb/u55/20260601_6a1d43367a592.png)
### 自动更新
![3915](https://s1.galgame.fun/imgb/u55/20260601_6a1d4537482b8.png)

## 下载

[Releases](https://github.com/Spade-sec/First/releases)

| 平台 | 文件 |
|------|------|
| macOS (Apple Silicon) | `First-ARM.dmg` |
| macOS (Intel) | `First-Intel.dmg` |
| Windows | `First-Windows.zip` |

## 支持的微信版本

### Windows

- WMPF 版本：11581, 11633, 13331, 13341, 13487, 13639, 13655, 13871, 13909, 14161, 14199, 14315, 16133, 16203, 16389, 16467, 16771, 16815, 16965, 17037, 17071, 17127, 18055, 18151, 18787, 18891, 18955, 19027, 19201（实时更新）
- 推荐微信版本：**4.1.0.30**
- 下载地址：[weixin/4.1.0.30](https://github.com/vs-olitus/wx-version/releases/tag/4.1.0.30)

### macOS

- WMPF 版本：18152, 18788（实时更新）
- 推荐微信版本：**4.1.7.30**
- 下载地址：[weixin/4.1.7.30](https://github.com/vs-olitus/wx-version/releases/tag/4.1.7.30)

## 快速开始

1. 打开 First
2. 点击启动 — Frida 自动注入微信
3. 在微信中打开小程序
4. 使用 DevTools / 云捕获 / 导航等功能

## macOS 注意事项

如果 Frida 注入报错，需要解除系统对进程附加的限制，任选其一：

**方案一：关闭 SIP（系统完整性保护）**

> 关闭后 Frida 才能正常注入进程。参考教程：[macOS SIP 开启关闭教程](https://cloud.tencent.com/developer/article/1496058)

**方案二：强制重签名 WeChat**

```bash
sudo codesign --force --deep --sign - /Applications/WeChat.app
```

## 参考

- [evi0s/WMPFDebugger](https://github.com/evi0s/WMPFDebugger)
- [0xsdeo/HeartK](https://github.com/0xsdeo/HeartK)
- [残笑/FindSomething](https://github.com/momosecurity/FindSomething)
- [进击的HACK / JSRPC 与调用 wx.cloud](https://mp.weixin.qq.com/s/hTlekrCPiMJCvsHYx7CAxw)
- [linguo2625469/WMPFDebugger-mac](https://github.com/linguo2625469/WMPFDebugger-mac)

## 致谢

感谢 **0xsdeo** 师傅的大力支持与思路提供。


---

## 交流群

群满 200 人后需要手动邀请，请加我拉群：

<img src="https://s1.galgame.fun/imgb/u55/20260601_6a1d196618084.png" alt="微信二维码" width="300" />
