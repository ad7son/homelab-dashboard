# Google Python 風格指南（繁體中文）

目錄

- [1 背景](#background)
- [2 Python 語言規則](#python-language-rules)
  - [2.1 Lint 靜態檢查](#lint)
    - [2.1.1 定義](#lint-definition)
    - [2.1.2 優點](#lint-pros)
    - [2.1.3 缺點](#lint-cons)
    - [2.1.4 採用決策](#lint-decision)
  - [2.2 匯入](#imports)
    - [2.2.1 定義](#imports-definition)
    - [2.2.2 優點](#imports-pros)
    - [2.2.3 缺點](#imports-cons)
    - [2.2.4 採用決策](#imports-decision)
      - [2.2.4.1 例外](#imports-exemptions)
  - [2.3 套件](#packages)
    - [2.3.1 優點](#packages-pros)
    - [2.3.2 缺點](#packages-cons)
    - [2.3.3 採用決策](#packages-decision)
  - [2.4 例外處理](#exceptions)
    - [2.4.1 定義](#exceptions-definition)
    - [2.4.2 優點](#exceptions-pros)
    - [2.4.3 缺點](#exceptions-cons)
    - [2.4.4 採用決策](#exceptions-decision)
  - [2.5 可變的全域狀態](#global-variables)
    - [2.5.1 定義](#global-variables-definition)
    - [2.5.2 優點](#global-variables-pros)
    - [2.5.3 缺點](#global-variables-cons)
    - [2.5.4 採用決策](#global-variables-decision)
  - [2.6 巢狀／區域／內部類別與函式](#nested-classes-functions)
    - [2.6.1 定義](#nested-classes-functions-definition)
    - [2.6.2 優點](#nested-classes-functions-pros)
    - [2.6.3 缺點](#nested-classes-functions-cons)
    - [2.6.4 採用決策](#nested-classes-functions-decision)
  - [2.7 推導式與產生器運算式](#comprehensions)
    - [2.7.1 定義](#comprehensions-definition)
    - [2.7.2 優點](#comprehensions-pros)
    - [2.7.3 缺點](#comprehensions-cons)
    - [2.7.4 採用決策](#comprehensions-decision)
  - [2.8 預設迭代器與運算子](#default-iterators-operators)
    - [2.8.1 定義](#default-iterators-operators-definition)
    - [2.8.2 優點](#default-iterators-operators-pros)
    - [2.8.3 缺點](#default-iterators-operators-cons)
    - [2.8.4 採用決策](#default-iterators-operators-decision)
  - [2.9 產生器](#generators)
    - [2.9.1 定義](#generators-definition)
    - [2.9.2 優點](#generators-pros)
    - [2.9.3 缺點](#generators-cons)
    - [2.9.4 採用決策](#generators-decision)
  - [2.10 Lambda 函式](#lambdas)
    - [2.10.1 定義](#lambdas-definition)
    - [2.10.2 優點](#lambdas-pros)
    - [2.10.3 缺點](#lambdas-cons)
    - [2.10.4 採用決策](#lambdas-decision)
  - [2.11 條件運算式](#conditional-expressions)
    - [2.11.1 定義](#conditional-expressions-definition)
    - [2.11.2 優點](#conditional-expressions-pros)
    - [2.11.3 缺點](#conditional-expressions-cons)
    - [2.11.4 採用決策](#conditional-expressions-decision)
  - [2.12 預設引數值](#default-arguments)
    - [2.12.1 定義](#default-arguments-definition)
    - [2.12.2 優點](#default-arguments-pros)
    - [2.12.3 缺點](#default-arguments-cons)
    - [2.12.4 採用決策](#default-arguments-decision)
  - [2.13 Property 屬性](#properties)
    - [2.13.1 定義](#properties-definition)
    - [2.13.2 優點](#properties-pros)
    - [2.13.3 缺點](#properties-cons)
    - [2.13.4 採用決策](#properties-decision)
  - [2.14 真／假值判斷](#truefalse-evaluations)
    - [2.14.1 定義](#truefalse-evaluations-definition)
    - [2.14.2 優點](#truefalse-evaluations-pros)
    - [2.14.3 缺點](#truefalse-evaluations-cons)
    - [2.14.4 採用決策](#truefalse-evaluations-decision)
  - [2.16 詞法作用域](#lexical-scoping)
    - [2.16.1 定義](#lexical-scoping-definition)
    - [2.16.2 優點](#lexical-scoping-pros)
    - [2.16.3 缺點](#lexical-scoping-cons)
    - [2.16.4 採用決策](#lexical-scoping-decision)
  - [2.17 函式與方法裝飾器](#decorators)
    - [2.17.1 定義](#decorators-definition)
    - [2.17.2 優點](#decorators-pros)
    - [2.17.3 缺點](#decorators-cons)
    - [2.17.4 採用決策](#decorators-decision)
  - [2.18 執行緒](#threading)
  - [2.19 進階特性](#power-features)
    - [2.19.1 定義](#power-features-definition)
    - [2.19.2 優點](#power-features-pros)
    - [2.19.3 缺點](#power-features-cons)
    - [2.19.4 採用決策](#power-features-decision)
  - [2.20 現代 Python：from \_\_future\_\_ 匯入](#modern-python)
    - [2.20.1 定義](#modern-python-definition)
    - [2.20.2 優點](#modern-python-pros)
    - [2.20.3 缺點](#modern-python-cons)
    - [2.20.4 採用決策](#modern-python-decision)
  - [2.21 帶有型別註記的程式碼](#typed-code)
    - [2.21.1 定義](#typed-code-definition)
    - [2.21.2 優點](#typed-code-pros)
    - [2.21.3 缺點](#typed-code-cons)
    - [2.21.4 採用決策](#typed-code-decision)
- [3 Python 風格規則](#python-style-rules)
  - [3.1 分號](#semicolons)
  - [3.2 行長](#line-length)
  - [3.3 圓括號](#parentheses)
  - [3.4 縮排](#indentation)
    - [3.4.1 項目序列中的尾端逗號？](#trailing-comma)
  - [3.5 空行](#blank-lines)
  - [3.6 空白](#whitespace)
  - [3.7 Shebang 行](#shebang-line)
  - [3.8 註解與文件字串](#documentation)
    - [3.8.1 文件字串](#docstrings)
    - [3.8.2 模組](#module-docs)
      - [3.8.2.1 測試模組](#test-docs)
    - [3.8.3 函式與方法](#function-docs)
      - [3.8.3.1 覆寫的方法](#overridden-method-docs)
    - [3.8.4 類別](#class-docs)
    - [3.8.5 區塊註解與行內註解](#comments)
    - [3.8.6 標點、拼字與文法](#punctuation-spelling-grammar)
  - [3.10 字串](#strings)
    - [3.10.1 日誌](#logging)
    - [3.10.2 錯誤訊息](#error-messages)
  - [3.11 檔案、Socket 與類似的有狀態資源](#files)
  - [3.12 TODO 註解](#todo)
  - [3.13 匯入格式](#imports-formatting)
  - [3.14 陳述式](#statements)
  - [3.15 Getter 與 Setter](#getters-and-setters)
  - [3.16 命名](#naming)
    - [3.16.1 應避免的名稱](#names-to-avoid)
    - [3.16.2 命名慣例](#naming-conventions)
      - [3.16.2.1 例外](#naming-exemptions)
    - [3.16.3 檔案命名](#file-naming)
    - [3.16.4 依 [Guido](https://en.wikipedia.org/wiki/Guido_van_Rossum) 建議衍生的指引](#guidelines-derived-from-guidos-recommendations)
    - [3.16.5 數學符號](#math-notation)
  - [3.17 主程式](#main)
  - [3.18 函式長度](#function-length)
  - [3.19 型別註記](#type-annotations)
    - [3.19.1 一般規則](#typing-general)
    - [3.19.2 換行](#typing-line-breaking)
    - [3.19.3 前向宣告](#forward-declarations)
    - [3.19.4 預設值](#typing-default-values)
    - [3.19.5 NoneType](#none-type)
    - [3.19.6 型別別名](#type-aliases)
    - [3.19.7 忽略型別檢查](#typing-ignore)
    - [3.19.8 變數的型別標註](#typing-variables)
    - [3.19.9 Tuple 與串列](#typing-tuples)
    - [3.19.10 型別變數](#typevars)
    - [3.19.11 字串型別](#typing-strings)
    - [3.19.12 型別標註所需的匯入](#typing-imports)
    - [3.19.13 條件式匯入](#typing-conditional-imports)
    - [3.19.14 循環相依](#typing-circular-deps)
    - [3.19.15 泛型](#generics)
- [4 結語](#consistency)

<a id="s1-background"></a>
<a id="1-background"></a>

<a id="background"></a>

## 1 背景

本風格指南列出撰寫 Python 程式時*應做與不應做的事*。團隊使用 [Black](https://github.com/psf/black) 或 [Pyink](https://github.com/google/pyink) 自動格式化工具，避免為排版爭論。（目前未確定）

<a id="s2-python-language-rules"></a>
<a id="2-python-language-rules"></a>

<a id="python-language-rules"></a>

## 2 Python 語言規則

<a id="s2.1-lint"></a>
<a id="21-lint"></a>

<a id="lint"></a>

### 2.1 Lint 靜態檢查

使用這份 [pylintrc](https://google.github.io/styleguide/pylintrc) 設定，對程式碼執行 `pylint`。

<a id="s2.1.1-definition"></a>
<a id="211-definition"></a>

<a id="lint-definition"></a>

#### 2.1.1 定義

`pylint` 是尋找 Python 原始碼中錯誤與風格問題的工具。它能找出 C、C++ 等動態性較低的語言通常由編譯器發現的問題。由於 Python 具有動態特性，有些警告可能不正確，但誤報應相當少見。

<a id="s2.1.2-pros"></a>
<a id="212-pros"></a>

<a id="lint-pros"></a>

#### 2.1.2 優點

能找出容易忽略的錯誤，例如拼字錯誤、變數尚未賦值便被使用等。

<a id="s2.1.3-cons"></a>
<a id="213-cons"></a>

<a id="lint-cons"></a>

#### 2.1.3 缺點

`pylint` 並不完美。為了發揮它的作用，有時需要調整寫法以配合它、停用警告，或修正工具本身。

<a id="s2.1.4-decision"></a>
<a id="214-decision"></a>

<a id="lint-decision"></a>

#### 2.1.4 採用決策

務必對程式碼執行 `pylint`。

不適用的警告應予停用，以免掩蓋其他問題。可以用行層級的註解停用警告：

<div class='goodcode'></div>

```python
def do_PUT(self):  # WSGI 規定的名稱，因此 pylint: disable=invalid-name
  ...
```

每個 `pylint` 警告都有符號名稱，例如 `empty-docstring`。Google 專用警告以 `g-` 開頭。

如果無法從符號名稱看出停用的原因，應補上說明。

這種停用方式的優點是容易搜尋，日後可以重新檢視。

執行下列指令可取得 `pylint` 警告清單：

```shell
pylint --list-msgs
```

若要進一步了解某則訊息，請使用：

```shell
pylint --help-msg=invalid-name
```

優先使用 `pylint: disable`，不要使用已棄用的舊格式 `pylint: disable-msg`。

可以在函式開頭刪除未使用的引數變數，以停用相關警告。務必加註解說明刪除原因；寫「未使用」即可。例如：

<div class='goodcode'></div>

```python
def viking_cafe_order(spam: str, beans: str, eggs: str | None = None) -> str:
    del beans, eggs  # vikings 不使用這些引數。
    return spam + spam + spam
```

其他常見做法包括將未使用的引數命名為 `_`、加上 `unused_` 前綴，或將它們賦值給 `_`。這些做法仍可使用，但已不再鼓勵：其中重新命名會破壞以名稱傳入引數的呼叫方式，而且這些做法無法確保引數確實未被使用。

<a id="s2.2-imports"></a>
<a id="22-imports"></a>

<a id="imports"></a>

### 2.2 匯入

`import` 陳述式只用來匯入套件與模組，不匯入個別型別、類別或函式。

<a id="s2.2.1-definition"></a>
<a id="221-definition"></a>

<a id="imports-definition"></a>

#### 2.2.1 定義

在模組之間共用程式碼的重用機制。

<a id="s2.2.2-pros"></a>
<a id="222-pros"></a>

<a id="imports-pros"></a>

#### 2.2.2 優點

命名空間的管理慣例簡單。每個識別字的來源都以一致方式呈現；`x.Obj` 表示物件 `Obj` 定義在模組 `x` 中。

<a id="s2.2.3-cons"></a>
<a id="223-cons"></a>

<a id="imports-cons"></a>

#### 2.2.3 缺點

模組名稱仍可能衝突。有些模組名稱長得不方便使用。

<a id="s2.2.4-decision"></a>
<a id="224-decision"></a>

<a id="imports-decision"></a>

#### 2.2.4 採用決策

*   使用 `import x` 匯入套件與模組。
*   使用 `from x import y`，其中 `x` 是套件前綴，`y` 是不含前綴的模組名稱。
*   下列情況可使用 `from x import y as z`：
    -   要匯入兩個都叫 `y` 的模組。
    -   `y` 與目前模組定義的頂層名稱衝突。
    -   `y` 與公開 API 中常見的參數名稱衝突，例如 `features`。
    -   `y` 名稱過長，不方便使用。
    -   `y` 在目前程式碼情境中過於籠統，例如 `from storage.file_system import options as fs_options`。
*   只有當 `z` 是標準縮寫時，才使用 `import y as z`，例如 `import numpy as np`。

例如，模組 `sound.effects.echo` 可如下匯入：

<div class='goodcode'></div>

```python
from sound.effects import echo
...
echo.EchoFilter(input, output, delay=0.7, atten=4)
```

匯入時不要使用相對名稱。即使模組位於同一套件中，也應使用完整套件名稱，避免不小心將同一套件匯入兩次。

<a id="imports-exemptions"></a>

##### 2.2.4.1 例外

下列模組中用來支援靜態分析與型別檢查的符號，不受此規則限制：

*   [`typing` 模組](#typing-imports)
*   [`collections.abc` 模組](#typing-imports)
*   [`typing_extensions` 模組](https://github.com/python/typing_extensions/blob/main/README.md)

<a id="s2.3-packages"></a>
<a id="23-packages"></a>

<a id="packages"></a>

### 2.3 套件

使用模組的完整路徑名稱匯入每個模組。

<a id="s2.3.1-pros"></a>
<a id="231-pros"></a>

<a id="packages-pros"></a>

#### 2.3.1 優點

避免模組名稱衝突，也避免因模組搜尋路徑不符作者預期而匯入錯誤模組，並使模組更容易尋找。

<a id="s2.3.2-cons"></a>
<a id="232-cons"></a>

<a id="packages-cons"></a>

#### 2.3.2 缺點

部署程式碼時必須重建套件階層，因此較麻煩；但對現代部署機制而言，這不算問題。

<a id="s2.3.3-decision"></a>
<a id="233-decision"></a>

<a id="packages-decision"></a>

#### 2.3.3 採用決策

所有新程式碼都應以完整套件名稱匯入各模組。

匯入方式應如下：

<div class='goodcode'></div>

```python
Yes:
  # 在程式碼中以完整名稱參照 absl.flags（較冗長）。
  import absl.flags
  from doctor.who import jodie

  _FOO = absl.flags.DEFINE_string(...)
```

<div class='goodcode'></div>

```python
Yes:
  # 在程式碼中只用模組名稱參照 flags（常見做法）。
  from absl import flags
  from doctor.who import jodie

  _FOO = flags.DEFINE_string(...)
```

*（假設這個檔案位於 `doctor/who/`，而 `jodie.py` 也位於該目錄。）*

<div class='badcode'></div>

```python
No:
  # 無法確定作者想用哪個模組，以及實際會匯入哪個模組。實際的
  # 匯入行為取決於控制 sys.path 的外部因素。
  # 作者究竟想匯入哪個 jodie 模組？
  import jodie
```

即使某些環境會這樣設定，也不應假設主程式所在目錄一定在 `sys.path` 中。因此，程式碼應將 `import jodie` 視為匯入名為 `jodie` 的第三方或頂層套件，而非本地的 `jodie.py`。

<a id="s2.4-exceptions"></a>
<a id="24-exceptions"></a>

<a id="exceptions"></a>

### 2.4 例外處理

可以使用例外，但必須謹慎。

<a id="s2.4.1-definition"></a>
<a id="241-definition"></a>

<a id="exceptions-definition"></a>

#### 2.4.1 定義

例外是一種跳離正常控制流程，以處理錯誤或其他異常情況的機制。

<a id="s2.4.2-pros"></a>
<a id="242-pros"></a>

<a id="exceptions-pros"></a>

#### 2.4.2 優點

正常操作的控制流程不會被錯誤處理程式碼打亂。發生特定情況時，也能跨越多層呼叫框架，例如一次離開 N 層巢狀函式，而不必逐層傳遞錯誤碼。

<a id="s2.4.3-cons"></a>
<a id="243-cons"></a>

<a id="exceptions-cons"></a>

#### 2.4.3 缺點

可能讓控制流程難以理解。呼叫函式庫時，容易遺漏錯誤情況。

<a id="s2.4.4-decision"></a>
<a id="244-decision"></a>

<a id="exceptions-decision"></a>

#### 2.4.4 採用決策

使用例外時必須符合下列條件：

-   適當時應使用內建例外類別。例如，驗證函式引數時若發現違反前置條件等程式設計錯誤，應引發 `ValueError`。

-   不要以 `assert` 陳述式取代條件判斷或前置條件驗證。應用程式邏輯不能仰賴它；一個檢驗方式是：移除 `assert` 也不應破壞程式。`assert` 條件[不保證會被求值](https://docs.python.org/3/reference/simple_stmts.html#the-assert-statement)。在使用 [pytest](https://pytest.org) 的測試中，以 `assert` 驗證預期結果則是適當且預期的做法。例如：

    <div class='goodcode'></div>

    ```python
    Yes:
      def connect_to_next_port(self, minimum: int) -> int:
        """連線至下一個可用連接埠。

        Args:
          minimum: 大於或等於 1024 的連接埠值。

        Returns:
          新的最小連接埠值。

        Raises:
          ConnectionError: 找不到可用的連接埠。
        """
        if minimum < 1024:
          # 注意，此處引發的 ValueError 未記錄於文件字串的
          # "Raises:" 區段，因為不適合保證誤用 API 時
          # 一定會出現這個特定反應。
          raise ValueError(f'Min. port must be at least 1024, not {minimum}.')
        port = self._find_next_open_port(minimum)
        if port is None:
          raise ConnectionError(
              f'Could not connect to service on port {minimum} or higher.')
        # 程式碼不依賴這個 assert 的結果。
        assert port >= minimum, (
            f'Unexpected port {port} when minimum was {minimum}.')
        return port
    ```

    <div class='badcode'></div>

    ```python
    No:
      def connect_to_next_port(self, minimum: int) -> int:
        """連線至下一個可用連接埠。

        Args:
          minimum: 大於或等於 1024 的連接埠值。

        Returns:
          新的最小連接埠值。
        """
        assert minimum >= 1024, 'Minimum port must be at least 1024.'
        # 下列程式碼依賴前面的 assert。
        port = self._find_next_open_port(minimum)
        assert port is not None
        # return 陳述式的型別檢查依賴這個 assert。
        return port
    ```

-   函式庫或套件可以定義自己的例外，但必須繼承既有例外類別。例外名稱應以 `Error` 結尾，且不應造成重複命名，例如 `foo.FooError`。

-   絕不可使用捕捉所有例外的 `except:`，或捕捉 `Exception`、`StandardError`，除非你正在：

    -   重新引發該例外；或
    -   建立程式中的隔離點，將例外記錄並抑制，而不向外傳播，例如保護執行緒最外層區塊，避免整個執行緒崩潰。

    Python 在這方面非常寬鬆，`except:` 真的會捕捉所有東西，包括拼錯的名稱、`sys.exit()` 呼叫、Ctrl+C 中斷、unittest 失敗，以及各種你其實不想捕捉的例外。

-   盡量縮小 `try`／`except` 區塊中的程式碼範圍。`try` 本體越大，就越可能由意料之外的程式碼引發例外；此時 `try`／`except` 會掩蓋真正的錯誤。

-   使用 `finally` 子句執行無論 `try` 是否引發例外都必須執行的程式碼。這通常適合用於清理工作，例如關閉檔案。

<a id="s2.5-global-variables"></a>
<a id="25-global-variables"></a>
<a id="s2.5-global-state"></a>
<a id="25-global-state"></a>

<a id="global-variables"></a>

### 2.5 可變的全域狀態

避免使用可變的全域狀態。

<a id="s2.5.1-definition"></a>
<a id="251-definition"></a>

<a id="global-variables-definition"></a>

#### 2.5.1 定義

程式執行期間可能被修改的模組層級值或類別屬性。

<a id="s2.5.2-pros"></a>
<a id="252-pros"></a>

<a id="global-variables-pros"></a>

#### 2.5.2 優點

偶爾有用。

<a id="s2.5.3-cons"></a>
<a id="253-cons"></a>

<a id="global-variables-cons"></a>

#### 2.5.3 缺點

*   破壞封裝：這種設計可能讓合理需求難以實現。例如，以全域狀態管理資料庫連線，會使同時連接兩個資料庫變得困難，例如遷移時需要比較差異的情境。全域登錄表也容易出現類似問題。

*   可能在匯入時改變模組行為，因為全域變數的賦值發生在首次匯入模組時。

<a id="s2.5.4-decision"></a>
<a id="254-decision"></a>

<a id="global-variables-decision"></a>

#### 2.5.4 採用決策

避免使用可變的全域狀態。

極少數確有理由使用全域狀態的情況下，可變的全域實體應宣告於模組層級或作為類別屬性，並在名稱前加 `_` 表示內部使用。若有必要，外部必須透過公開函式或類別方法存取可變的全域狀態。參見下方[命名](#s3.16-naming)。請以註解，或由註解連結的文件，說明使用可變全域狀態的設計理由。

允許且鼓勵使用模組層級常數。例如，內部使用的常數 `_MAX_HOLY_HANDGRENADE_COUNT = 3`，或公開 API 常數 `SIR_LANCELOTS_FAVORITE_COLOR = "blue"`。常數必須使用全大寫字母與底線命名。參見下方[命名](#s3.16-naming)。

<a id="s2.6-nested"></a>
<a id="26-nested"></a>

<a id="nested-classes-functions"></a>

### 2.6 巢狀／區域／內部類別與函式

當需要捕捉區域變數形成閉包時，可以使用巢狀區域函式或類別。也可以使用內部類別。

<a id="s2.6.1-definition"></a>
<a id="261-definition"></a>

<a id="nested-classes-functions-definition"></a>

#### 2.6.1 定義

類別可以定義在方法、函式或類別內。函式可以定義在方法或函式內。巢狀函式能以唯讀方式存取外層作用域中定義的變數。

<a id="s2.6.2-pros"></a>
<a id="262-pros"></a>

<a id="nested-classes-functions-pros"></a>

#### 2.6.2 優點

可以定義只在極小範圍內使用的輔助類別與函式，很符合[抽象資料型別（ADT）](https://en.wikipedia.org/wiki/Abstract_data_type)的概念。常用於實作裝飾器。

<a id="s2.6.3-cons"></a>
<a id="263-cons"></a>

<a id="nested-classes-functions-cons"></a>

#### 2.6.3 缺點

巢狀函式與類別無法直接測試。巢狀結構可能使外層函式更長、更難閱讀。

<a id="s2.6.4-decision"></a>
<a id="264-decision"></a>

<a id="nested-classes-functions-decision"></a>

#### 2.6.4 採用決策

可以使用，但有一些限制。除非需要捕捉 `self` 或 `cls` 以外的區域值形成閉包，否則應避免巢狀函式或類別。不要只是為了對模組使用者隱藏函式而將它巢狀定義；改為在模組層級定義，並在名稱前加 `_`，讓測試仍能存取。

<a id="s2.7-comprehensions"></a>
<a id="s2.7-list_comprehensions"></a>
<a id="27-list_comprehensions"></a>
<a id="list_comprehensions"></a>
<a id="list-comprehensions"></a>

<a id="comprehensions"></a>

### 2.7 推導式與產生器運算式

簡單情況下可以使用。

<a id="s2.7.1-definition"></a>
<a id="271-definition"></a>

<a id="comprehensions-definition"></a>

#### 2.7.1 定義

List、Dict、Set 推導式與產生器運算式，提供簡潔而有效率的方式來建立容器型別及迭代器，不必使用傳統迴圈、`map()`、`filter()` 或 `lambda`。

<a id="s2.7.2-pros"></a>
<a id="272-pros"></a>

<a id="comprehensions-pros"></a>

#### 2.7.2 優點

簡單推導式可能比其他建立 dict、list 或 set 的方法更清楚、更簡單。產生器運算式完全避免建立串列，因此可能非常有效率。

<a id="s2.7.3-cons"></a>
<a id="273-cons"></a>

<a id="comprehensions-cons"></a>

#### 2.7.3 缺點

複雜的推導式或產生器運算式可能難以閱讀。

<a id="s2.7.4-decision"></a>
<a id="274-decision"></a>

<a id="comprehensions-decision"></a>

#### 2.7.4 採用決策

允許使用推導式，但不允許多個 `for` 子句或篩選運算式。應優先考量可讀性，而非簡短。

<div class='goodcode'></div>

```python
Yes:
  result = [mapping_expr for value in iterable if filter_expr]

  result = [
      is_valid(metric={'key': value})
      for value in interesting_iterable
      if a_longer_filter_expression(value)
  ]

  descriptive_name = [
      transform({'key': key, 'value': value}, color='black')
      for key, value in generate_iterable(some_input)
      if complicated_condition_is_met(key, value)
  ]

  result = []
  for x in range(10):
    for y in range(5):
      if x * y > 10:
        result.append((x, y))

  return {
      x: complicated_transform(x)
      for x in long_generator_function(parameter)
      if x is not None
  }

  return (x**2 for x in range(10))

  unique_names = {user.name for user in users if user is not None}
```

<div class='badcode'></div>

```python
No:
  result = [(x, y) for x in range(10) for y in range(5) if x * y > 10]

  return (
      (x, y, z)
      for x in range(5)
      for y in range(5)
      if x != y
      for z in range(5)
      if y != z
  )
```

<a id="s2.8-default-iterators-and-operators"></a>

<a id="default-iterators-operators"></a>

### 2.8 預設迭代器與運算子

對支援的型別使用預設迭代器與運算子，例如串列、字典及檔案。

<a id="s2.8.1-definition"></a>
<a id="281-definition"></a>

<a id="default-iterators-operators-definition"></a>

#### 2.8.1 定義

字典、串列等容器型別，會定義預設迭代器與成員測試運算子（`in` 和 `not in`）。

<a id="s2.8.2-pros"></a>
<a id="282-pros"></a>

<a id="default-iterators-operators-pros"></a>

#### 2.8.2 優點

預設迭代器與運算子簡單而有效率，能直接表達操作，不需要額外的方法呼叫。使用預設運算子的函式具有通用性，可用於任何支援該操作的型別。

<a id="s2.8.3-cons"></a>
<a id="283-cons"></a>

<a id="default-iterators-operators-cons"></a>

#### 2.8.3 缺點

無法從方法名稱看出物件型別，除非變數有型別註記。這同時也是優點。

<a id="s2.8.4-decision"></a>
<a id="284-decision"></a>

<a id="default-iterators-operators-decision"></a>

#### 2.8.4 採用決策

對支援的型別使用預設迭代器與運算子，例如串列、字典及檔案。內建型別也提供迭代器方法；相較於回傳串列的方法，應優先使用這些方法，但不應在迭代容器時修改該容器。

<div class='goodcode'></div>

```python
Yes:  for key in adict: ...
      if obj in alist: ...
      for line in afile: ...
      for k, v in adict.items(): ...
```

<div class='badcode'></div>

```python
No:   for key in adict.keys(): ...
      for line in afile.readlines(): ...
```

<a id="s2.9-generators"></a>
<a id="29-generators"></a>

<a id="generators"></a>

### 2.9 產生器

依需要使用產生器。

<a id="s2.9.1-definition"></a>
<a id="291-definition"></a>

<a id="generators-definition"></a>

#### 2.9.1 定義

產生器函式回傳迭代器，每執行一次 `yield` 陳述式便產出一個值。產出值後，產生器函式的執行狀態會暫停，直到需要下一個值。

<a id="s2.9.2-pros"></a>
<a id="292-pros"></a>

<a id="generators-pros"></a>

#### 2.9.2 優點

每次呼叫之間都保留區域變數與控制流程的狀態，因此程式碼較簡單。相較於一次建立完整串列的函式，產生器使用較少記憶體。

<a id="s2.9.3-cons"></a>
<a id="293-cons"></a>

<a id="generators-cons"></a>

#### 2.9.3 缺點

產生器中的區域變數，要等產生器耗盡或產生器本身被垃圾回收，才會被垃圾回收。

<a id="s2.9.4-decision"></a>
<a id="294-decision"></a>

<a id="generators-decision"></a>

#### 2.9.4 採用決策

可以使用。產生器函式的文件字串應使用 `Yields:`，而非 `Returns:`。

如果產生器管理昂貴的資源，務必強制執行清理工作。

一個好的清理方式，是用情境管理器包裝產生器，參見 [PEP-0533](https://peps.python.org/pep-0533/)。

<a id="s2.10-lambda-functions"></a>
<a id="210-lambda-functions"></a>

<a id="lambdas"></a>

### 2.10 Lambda 函式

單行內容可以使用。相較於搭配 `lambda` 的 `map()` 或 `filter()`，優先使用產生器運算式。

<a id="s2.10.1-definition"></a>
<a id="2101-definition"></a>

<a id="lambdas-definition"></a>

#### 2.10.1 定義

Lambda 以運算式而非陳述式定義匿名函式。

<a id="s2.10.2-pros"></a>
<a id="2102-pros"></a>

<a id="lambdas-pros"></a>

#### 2.10.2 優點

方便。

<a id="s2.10.3-cons"></a>
<a id="2103-cons"></a>

<a id="lambdas-cons"></a>

#### 2.10.3 缺點

比區域函式更難閱讀與除錯。缺乏名稱使堆疊追蹤更難理解；函式只能包含一個運算式，因此表達能力有限。

<a id="s2.10.4-decision"></a>
<a id="2104-decision"></a>

<a id="lambdas-decision"></a>

#### 2.10.4 採用決策

允許使用 lambda。如果 lambda 函式中的程式碼跨越多行，或長於 60 至 80 個字元，改為一般的[巢狀函式](#lexical-scoping)可能更好。

乘法等常見操作，應使用 `operator` 模組中的函式，而非 lambda。例如，優先使用 `operator.mul`，而非 `lambda x, y: x * y`。

<a id="s2.11-conditional-expressions"></a>
<a id="211-conditional-expressions"></a>

<a id="conditional-expressions"></a>

### 2.11 條件運算式

簡單情況下可以使用。

<a id="s2.11.1-definition"></a>
<a id="2111-definition"></a>

<a id="conditional-expressions-definition"></a>

#### 2.11.1 定義

條件運算式有時稱為「三元運算子」，提供比 if 陳述式更短的語法，例如 `x = 1 if cond else 2`。

<a id="s2.11.2-pros"></a>
<a id="2112-pros"></a>

<a id="conditional-expressions-pros"></a>

#### 2.11.2 優點

比 if 陳述式更短、更方便。

<a id="s2.11.3-cons"></a>
<a id="2113-cons"></a>

<a id="conditional-expressions-cons"></a>

#### 2.11.3 缺點

可能比 if 陳述式難讀。運算式很長時，條件可能不容易找到。

<a id="s2.11.4-decision"></a>
<a id="2114-decision"></a>

<a id="conditional-expressions-decision"></a>

#### 2.11.4 採用決策

簡單情況下可以使用。條件成立時的運算式、if 條件運算式及 else 運算式，各部分都必須能放在單行中。情況較複雜時，使用完整的 if 陳述式。

<div class='goodcode'></div>

```python
Yes:
    one_line = 'yes' if predicate(value) else 'no'
    slightly_split = ('yes' if predicate(value)
                      else 'no, nein, nyet')
    the_longest_ternary_style_that_can_be_done = (
        'yes, true, affirmative, confirmed, correct'
        if predicate(value)
        else 'no, false, negative, nay')
```

<div class='badcode'></div>

```python
No:
    bad_line_breaking = ('yes' if predicate(value) else
                         'no')
    portion_too_long = ('yes'
                        if some_long_module.some_long_predicate_function(
                            really_long_variable_name)
                        else 'no, false, negative, nay')
```

<a id="s2.12-default-argument-values"></a>
<a id="212-default-argument-values"></a>

<a id="default-arguments"></a>

### 2.12 預設引數值

大多數情況下可以使用。

<a id="s2.12.1-definition"></a>
<a id="2121-definition"></a>

<a id="default-arguments-definition"></a>

#### 2.12.1 定義

可以在函式參數串列尾端指定變數的預設值，例如 `def foo(a, b=0):`。呼叫 `foo` 時若只傳入一個引數，`b` 為 0；若傳入兩個引數，`b` 就是第二個引數的值。

<a id="s2.12.2-pros"></a>
<a id="2122-pros"></a>

<a id="default-arguments-pros"></a>

#### 2.12.2 優點

函式常有許多預設值，只有少數情況需要覆寫。預設引數值讓這件事很容易，不必為少見的例外情況定義大量函式。Python 不支援方法／函式多載，因此預設引數是簡單的「模擬」多載方式。

<a id="s2.12.3-cons"></a>
<a id="2123-cons"></a>

<a id="default-arguments-cons"></a>

#### 2.12.3 缺點

預設引數在載入模組時只求值一次。如果引數是串列或字典等可變物件，可能產生問題：函式若修改物件，例如向串列加入項目，預設值也會被修改。

<a id="s2.12.4-decision"></a>
<a id="2124-decision"></a>

<a id="default-arguments-decision"></a>

#### 2.12.4 採用決策

可以使用，但有下列限制：

定義函式或方法時，不要使用可變物件作為預設值。

<div class='goodcode'></div>

```python
Yes: def foo(a, b=None):
         if b is None:
             b = []
Yes: def foo(a, b: Sequence | None = None):
         if b is None:
             b = []
Yes: def foo(a, b: Sequence = ()):  # 空 tuple 可以使用，因為 tuple 不可變。
         ...
```

<div class='badcode'></div>

```python
from absl import flags
_FOO = flags.DEFINE_string(...)

No:  def foo(a, b=[]):
         ...
No:  def foo(a, b=time.time()):  # `b` 應該表示這個模組載入時的時間嗎？
         ...
No:  def foo(a, b=_FOO.value):  # sys.argv 尚未被解析……
         ...
No:  def foo(a, b: Mapping = {}):  # 仍可能傳入未經檢查的程式碼。
         ...
```

<a id="s2.13-properties"></a>
<a id="213-properties"></a>

<a id="properties"></a>

### 2.13 Property 屬性

對於只需簡單計算或邏輯的屬性讀取與設定，可以使用 property。其實作必須符合一般屬性存取的預期：成本低、直接，且不會出人意料。

<a id="s2.13.1-definition"></a>
<a id="2131-definition"></a>

<a id="properties-definition"></a>

#### 2.13.1 定義

將讀取與設定屬性的方法呼叫，包裝成標準屬性存取的方式。

<a id="s2.13.2-pros"></a>
<a id="2132-pros"></a>

<a id="properties-pros"></a>

#### 2.13.2 優點

*   提供屬性讀取與賦值的 API，而不必呼叫 [getter 與 setter](#getters-and-setters) 方法。
*   可將屬性設為唯讀。
*   允許延遲計算。
*   當內部實作在不影響類別使用者的情況下演進時，提供維持類別公開介面的方式。

<a id="s2.13.3-cons"></a>
<a id="2133-cons"></a>

<a id="properties-cons"></a>

#### 2.13.3 缺點

*   像運算子多載一樣，可能隱藏副作用。
*   可能讓子類別的行為難以理解。

<a id="s2.13.4-decision"></a>
<a id="2134-decision"></a>

<a id="properties-decision"></a>

#### 2.13.4 採用決策

允許使用 property，但如同運算子多載，只應在必要時使用，且必須符合典型屬性存取的預期；其他情況應遵循 [getter 與 setter](#getters-and-setters) 規則。

例如，不允許只為了讀取與設定內部屬性而使用 property：沒有任何計算，因此沒有必要（應[直接將屬性公開](#getters-and-setters)）。相較之下，用 property 控制屬性存取或計算*簡單的*衍生值則可以，因為邏輯簡單且符合預期。

應以 `@property` [裝飾器](#s2.17-function-and-method-decorators)建立 property。手動實作 property 描述器屬於[進階特性](#power-features)。

結合 property 的繼承行為可能不明顯。不要用 property 實作子類別未來可能需要覆寫或擴充的計算。

<a id="s2.14-truefalse-evaluations"></a>
<a id="214-truefalse-evaluations"></a>

<a id="truefalse-evaluations"></a>

### 2.14 真／假值判斷

盡可能使用「隱含」的假值判斷，但有少數注意事項。

<a id="s2.14.1-definition"></a>
<a id="2141-definition"></a>

<a id="truefalse-evaluations-definition"></a>

#### 2.14.1 定義

在布林情境下，Python 會將某些值判定為 `False`。簡單經驗法則是：所有「空」的值皆為假，因此 `0, None, [], {}, ''` 在布林情境下都會判定為假。

<a id="s2.14.2-pros"></a>
<a id="2142-pros"></a>

<a id="truefalse-evaluations-pros"></a>

#### 2.14.2 優點

使用 Python 布林判斷的條件更容易閱讀，也較不易出錯；大多數情況下也更快。

<a id="s2.14.3-cons"></a>
<a id="2143-cons"></a>

<a id="truefalse-evaluations-cons"></a>

#### 2.14.3 缺點

對 C／C++ 開發者而言可能看起來不習慣。

<a id="s2.14.4-decision"></a>
<a id="2144-decision"></a>

<a id="truefalse-evaluations-decision"></a>

#### 2.14.4 採用決策

盡可能使用「隱含」假值，例如使用 `if foo:`，而非 `if foo != []:`。但應注意下列事項：

-   檢查 `None` 時，一律使用 `if foo is None:` 或 `is not None`。例如，檢查預設為 `None` 的變數或引數是否已設成其他值；其他值在布林情境下也可能是假值！

-   不要用 `==` 將布林變數與 `False` 比較，應使用 `if not x:`。若須區分 `False` 與 `None`，則組合條件，例如 `if not x and x is not None:`。

-   對序列（字串、串列、tuple），利用空序列為假的特性；應優先使用 `if seq:` 及 `if not seq:`，而非 `if len(seq):` 及 `if not len(seq):`。

-   處理整數時，隱含假值判斷可能弊大於利，例如不小心將 `None` 當成 0。如果已知值是整數，且不是 `len()` 的結果，可以與整數 0 比較。

    <div class='goodcode'></div>

    ```python
    Yes: if not users:
             print('no users')

         if i % 10 == 0:
             self.handle_multiple_of_ten()

         def f(x=None):
             if x is None:
                 x = []
    ```

    <div class='badcode'></div>

    ```python
    No:  if len(users) == 0:
             print('no users')

         if not i % 10:
             self.handle_multiple_of_ten()

         def f(x=None):
             x = x or []
    ```

-   注意，`'0'`（字串形式的 0）會判定為真。

-   注意，NumPy 陣列在隱含布林情境下可能引發例外。檢查 `np.array` 是否為空，應優先使用 `.size` 屬性，例如 `if not users.size`。

<a id="s2.16-lexical-scoping"></a>
<a id="216-lexical-scoping"></a>

<a id="lexical-scoping"></a>

### 2.16 詞法作用域

可以使用。

<a id="s2.16.1-definition"></a>
<a id="2161-definition"></a>

<a id="lexical-scoping-definition"></a>

#### 2.16.1 定義

Python 巢狀函式可以參照外層函式定義的變數，但不能對它們賦值。變數繫結以詞法作用域解析，也就是依據靜態程式文字決定。在一個區塊中對某名稱的任何賦值，都會讓 Python 將該名稱的所有參照視為區域變數，即使使用發生在賦值之前。如果有 global 宣告，該名稱就會被視為全域變數。

此特性的使用範例如下：

<div class='goodcode'></div>

```python
def get_adder(summand1: float) -> Callable[[float], float]:
    """回傳一個將數字加到指定數字上的函式。"""
    def adder(summand2: float) -> float:
        return summand1 + summand2

    return adder
```

<a id="s2.16.2-pros"></a>
<a id="2162-pros"></a>

<a id="lexical-scoping-pros"></a>

#### 2.16.2 優點

通常能產生更清楚、更優雅的程式碼。熟悉 Lisp、Scheme，以及 Haskell、ML 等語言的程式設計者，尤其容易適應。

<a id="s2.16.3-cons"></a>
<a id="2163-cons"></a>

<a id="lexical-scoping-cons"></a>

#### 2.16.3 缺點

可能造成令人困惑的錯誤，例如這個取自 [PEP-0227](https://peps.python.org/pep-0227/) 的例子：

<div class='badcode'></div>

```python
i = 4
def foo(x: Iterable[int]):
    def bar():
        print(i, end='')
    # ...
    # 此處有許多程式碼
    # ...
    for i in x:  # 原來 i 確實是 foo 的區域變數，因此 bar 看到的是它
        print(i, end='')
    bar()
```

因此 `foo([1, 2, 3])` 會印出 `1 2 3 3`，而非 `1 2 3 4`。

<a id="s2.16.4-decision"></a>
<a id="2164-decision"></a>

<a id="lexical-scoping-decision"></a>

#### 2.16.4 採用決策

可以使用。

<a id="s2.17-function-and-method-decorators"></a>
<a id="217-function-and-method-decorators"></a>
<a id="function-and-method-decorators"></a>

<a id="decorators"></a>

### 2.17 函式與方法裝飾器

有明確好處時，審慎使用裝飾器。避免 `staticmethod`，並限制 `classmethod` 的使用。

<a id="s2.17.1-definition"></a>
<a id="2171-definition"></a>

<a id="decorators-definition"></a>

#### 2.17.1 定義

[函式與方法裝飾器](https://docs.python.org/3/glossary.html#term-decorator)，也就是「`@` 語法」。常見例子是 `@property`，用來將一般方法轉成動態計算的屬性。裝飾器語法也允許使用者自行定義裝飾器。具體而言，對某個函式 `my_decorator`，下列寫法：

<div class='goodcode'></div>

```python
class C:
    @my_decorator
    def method(self):
        # 方法本體……
```

等同於：

<div class='goodcode'></div>

```python
class C:
    def method(self):
        # 方法本體……
    method = my_decorator(method)
```

<a id="s2.17.2-pros"></a>
<a id="2172-pros"></a>

<a id="decorators-pros"></a>

#### 2.17.2 優點

能優雅地指定對方法的轉換，例如消除重複程式碼、強制維持不變條件等。

<a id="s2.17.3-cons"></a>
<a id="2173-cons"></a>

<a id="decorators-cons"></a>

#### 2.17.3 缺點

裝飾器可以任意操作函式引數或回傳值，造成出乎意料的隱含行為。此外，裝飾器在物件定義時執行；對模組層級物件，例如類別與模組函式，這發生在匯入時。裝飾器程式碼發生失敗時，幾乎無法復原。

<a id="s2.17.4-decision"></a>
<a id="2174-decision"></a>

<a id="decorators-decision"></a>

#### 2.17.4 採用決策

有明確好處時，審慎使用裝飾器。裝飾器應遵循與函式相同的匯入及命名規則。裝飾器的文件字串應明確說明該函式是裝飾器，並應為裝飾器撰寫單元測試。

避免裝飾器本身依賴外部資源，例如檔案、socket 或資料庫連線，因為裝飾器執行時，這些資源可能不可用；例如由 `pydoc` 或其他工具觸發匯入時。只要傳入合法參數，裝飾器就應盡可能保證在所有情況下都成功。

裝飾器是「頂層程式碼」的特殊情況，進一步討論見 [main](#s3.17-main)。

除非為了整合既有函式庫定義的 API 而不得不使用，否則不要使用 `staticmethod`；應改寫為模組層級函式。

只有在撰寫具名建構函式，或修改必要全域狀態的類別專用程序，例如處理程序範圍的快取時，才使用 `classmethod`。

<a id="s2.18-threading"></a>
<a id="218-threading"></a>

<a id="threading"></a>

### 2.18 執行緒

不要依賴內建型別操作的原子性。

雖然字典等 Python 內建資料型別的操作看似具有原子性，但某些邊界情況並非如此，例如 `__hash__` 或 `__eq__` 以 Python 方法實作時，因此不應依賴其原子性。也不應依賴變數賦值的原子性，因為這又仰賴字典。

執行緒之間傳遞資料，優先使用 `queue` 模組的 `Queue` 資料型別。其他情況使用 `threading` 模組及其鎖定原語。相較於底層鎖，應優先使用條件變數與 `threading.Condition`。

<a id="s2.19-power-features"></a>
<a id="219-power-features"></a>

<a id="power-features"></a>

### 2.19 進階特性

避免這些特性。

<a id="s2.19.1-definition"></a>
<a id="2191-definition"></a>

<a id="power-features-definition"></a>

#### 2.19.1 定義

Python 極為靈活，提供許多花俏特性，例如自訂 metaclass、存取 bytecode、即時編譯、動態繼承、改變物件的父類別、匯入技巧、反射（例如 `getattr()` 的部分用法）、修改系統內部、透過 `__del__` 方法自訂清理工作等。

<a id="s2.19.2-pros"></a>
<a id="2192-pros"></a>

<a id="power-features-pros"></a>

#### 2.19.2 優點

這些是強大的語言特性，能讓程式碼更精簡。

<a id="s2.19.3-cons"></a>
<a id="2193-cons"></a>

<a id="power-features-cons"></a>

#### 2.19.3 缺點

即使並非必要，這些「酷炫」特性也很容易讓人想使用。底層採用不常見特性的程式碼更難閱讀、理解與除錯。原作者最初可能不這麼覺得，但日後重新檢視時，通常會比更長卻直白的程式碼難懂。

<a id="s2.19.4-decision"></a>
<a id="2194-decision"></a>

<a id="power-features-decision"></a>

#### 2.19.4 採用決策

避免在程式碼中使用這些特性。

可以使用內部採用這些特性的標準函式庫模組與類別，例如 `abc.ABCMeta`、`dataclasses` 及 `enum`。

<a id="s2.20-modern-python"></a>
<a id="220-modern-python"></a>

<a id="modern-python"></a>

### 2.20 現代 Python：from \_\_future\_\_ 匯入

新語言版本的語意變更，可能透過特殊的 future 匯入，在較舊執行環境中逐一檔案啟用。

<a id="s2.20.1-definition"></a>
<a id="2201-definition"></a>

<a id="modern-python-definition"></a>

#### 2.20.1 定義

透過 `from __future__ import` 陳述式啟用較新的特性，可以提早使用預期在未來 Python 版本提供的功能。

<a id="s2.20.2-pros"></a>
<a id="2202-pros"></a>

<a id="modern-python-pros"></a>

#### 2.20.2 優點

實務證明這能讓執行環境升級更平順：可以逐一檔案修改，同時宣告相容性並避免檔案內發生退步。現代化程式碼更容易維護，較不會累積未來升級執行環境時難以處理的技術債。

<a id="s2.20.3-cons"></a>
<a id="2203-cons"></a>

<a id="modern-python-cons"></a>

#### 2.20.3 缺點

這類程式碼可能無法在引入所需 future 陳述式以前的非常舊版直譯器上執行。支援極廣泛環境的專案較常遇到這種需求。

<a id="s2.20.4-decision"></a>
<a id="2204-decision"></a>

<a id="modern-python-decision"></a>

#### 2.20.4 採用決策

<a id="from-future-imports"></a>

##### from \_\_future\_\_ 匯入

鼓勵使用 `from __future__ import` 陳述式，讓個別原始碼檔案現在就能使用較新的 Python 語法特性。當不再需要支援必須透過 `__future__` 匯入才能啟用該特性的版本時，可移除這些行。

如果程式碼可能在最低 3.5 的版本執行，而非僅支援 >= 3.7，請匯入：

<div class='goodcode'></div>

```python
from __future__ import generator_stop
```

更多資訊請閱讀 [Python future 陳述式定義](https://docs.python.org/3/library/__future__.html)文件。

除非確定程式碼只會在足夠新的環境執行，否則請勿移除這些匯入。即使目前未使用某個 future 匯入所啟用的特性，保留它仍能避免日後修改不小心依賴舊行為。

其他 `from __future__` 匯入陳述式，可依需要使用。

<a id="s2.21-type-annotated-code"></a>
<a id="s2.21-typed-code"></a>
<a id="221-type-annotated-code"></a>
<a id="typed-code"></a>

<a id="typed-code"></a>

### 2.21 帶有型別註記的程式碼

可以使用[型別提示](https://docs.python.org/3/library/typing.html)標註 Python 程式碼，並在建置時使用 [pyrefly](https://pyrefly.org/) 等型別檢查工具。多數情況下，若可行，型別註記應寫在原始碼檔案中。第三方模組或擴充模組的註記，可以放在 [stub `.pyi` 檔案](https://peps.python.org/pep-0484/#stub-files)中。

<a id="s2.21.1-definition"></a>
<a id="2211-definition"></a>

<a id="typed-code-definition"></a>

#### 2.21.1 定義

型別註記（或「型別提示」）用於函式或方法的引數及回傳值：

<div class='goodcode'></div>

```python
def func(a: int) -> list[int]:
```

也可以用類似語法宣告變數型別：

<div class='goodcode'></div>

```python
a: SomeType = some_func()
```

<a id="s2.21.2-pros"></a>
<a id="2212-pros"></a>

<a id="typed-code-pros"></a>

#### 2.21.2 優點

型別註記能改善可讀性與可維護性。型別檢查器能將許多執行階段錯誤轉為建置階段錯誤，也會限制使用[進階特性](#power-features)的能力。

<a id="s2.21.3-cons"></a>
<a id="2213-cons"></a>

<a id="typed-code-cons"></a>

#### 2.21.3 缺點

必須持續更新型別宣告。你可能遇到自己認為合法的程式碼卻出現型別錯誤。使用型別檢查器可能限制使用[進階特性](#power-features)的能力。

<a id="s2.21.4-decision"></a>
<a id="2214-decision"></a>

<a id="typed-code-decision"></a>

#### 2.21.4 採用決策

強烈鼓勵在更新程式碼時啟用 Python 型別分析。新增或修改公開 API 時，應加入型別註記，並在建置系統啟用型別檢查。由於靜態分析對 Python 而言相對較新，我們理解某些不期望的副作用，例如型別推斷錯誤，可能阻礙部分專案採用。在這種情況下，鼓勵作者在適當位置的 BUILD 檔案或程式碼中，加入 TODO 註解或問題追蹤連結，說明目前阻礙採用型別註記的問題。

<a id="s3-python-style-rules"></a>
<a id="3-python-style-rules"></a>

<a id="python-style-rules"></a>

## 3 Python 風格規則

<a id="s3.1-semicolons"></a>
<a id="31-semicolons"></a>

<a id="semicolons"></a>

### 3.1 分號

不要在行尾加分號，也不要用分號將兩個陳述式放在同一行。

<a id="s3.2-line-length"></a>
<a id="32-line-length"></a>

<a id="line-length"></a>

### 3.2 行長

每行最長為 *80 個字元*。

80 字元限制的明確例外：

-   很長的匯入陳述式。
-   註解中的 URL、路徑或很長的旗標。
-   不含空白、難以跨行拆分的模組層級長字串常數，例如 URL 或路徑。
-   停用 Pylint 的註解，例如 `# pylint: disable=invalid-name`。

不要用反斜線[明確接續行](https://docs.python.org/3/reference/lexical_analysis.html#explicit-line-joining)。

改用 Python 在[圓括號、方括號與大括號內的隱含接續行](http://docs.python.org/reference/lexical_analysis.html#implicit-line-joining)。必要時，可在運算式外多加一對圓括號。

注意，這條規則不禁止字串中以反斜線跳脫換行，參見[下文](#strings)。

<div class='goodcode'></div>

```python
Yes: foo_bar(self, width, height, color='black', design=None, x='foo',
             emphasis=None, highlight=0)
```

<div class='goodcode'></div>

```python

Yes: if (width == 0 and height == 0 and
         color == 'red' and emphasis == 'strong'):

     (bridge_questions.clarification_on
      .average_airspeed_of.unladen_swallow) = 'African or European?'

     with (
         very_long_first_expression_function() as spam,
         very_long_second_expression_function() as beans,
         third_thing() as eggs,
     ):
       place_order(eggs, beans, spam, beans)
```

<div class='badcode'></div>

```python

No:  if width == 0 and height == 0 and \
         color == 'red' and emphasis == 'strong':

     bridge_questions.clarification_on \
         .average_airspeed_of.unladen_swallow = 'African or European?'

     with very_long_first_expression_function() as spam, \
           very_long_second_expression_function() as beans, \
           third_thing() as eggs:
       place_order(eggs, beans, spam, beans)
```

字串常值無法放在單行時，使用圓括號進行隱含接續行。

<div class='goodcode'></div>

```python
x = ('This will build a very long long '
     'long long long long long long string')
```

盡可能在最高語法層級換行。如果必須換行兩次，兩次應在相同語法層級換行。

<div class='goodcode'></div>

```python
Yes: bridgekeeper.answer(
         name="Arthur", quest=questlib.find(owner="Arthur", perilous=True))

     answer = (a_long_line().of_chained_methods()
               .that_eventually_provides().an_answer())

     if (
         config is None
         or 'editor.language' not in config
         or config['editor.language'].use_spaces is False
     ):
       use_tabs()
```

<div class='badcode'></div>

```python
No: bridgekeeper.answer(name="Arthur", quest=questlib.find(
        owner="Arthur", perilous=True))

    answer = a_long_line().of_chained_methods().that_eventually_provides(
        ).an_answer()

    if (config is None or 'editor.language' not in config or config[
        'editor.language'].use_spaces is False):
      use_tabs()

```

註解中若有需要，將長 URL 獨立放在一行。

<div class='goodcode'></div>

```python
Yes:  # 詳細資訊見
      # http://www.example.com/us/developer/documentation/api/content/v2.0/csv_file_name_extension_full_specification.html
```

<div class='badcode'></div>

```python
No:  # 詳細資訊見
     # http://www.example.com/us/developer/documentation/api/content/\
     # v2.0/csv_file_name_extension_full_specification.html
```

請注意前述接續行範例中元素的縮排；說明見[縮排](#s3.4-indentation)一節。

[文件字串](#docstrings)的摘要行必須維持在 80 個字元內。

其他情況下，若某行超過 80 個字元，且 [Black](https://github.com/psf/black) 或 [Pyink](https://github.com/google/pyink) 自動格式化工具無法將其縮到限制內，允許超過此上限。合理時，仍鼓勵作者依上述指引手動拆行。

<a id="s3.3-parentheses"></a>
<a id="33-parentheses"></a>

<a id="parentheses"></a>

### 3.3 圓括號

節制使用圓括號。

tuple 外可以加圓括號，但不是必要。除非用於隱含接續行或表示 tuple，否則不要在 return 或條件陳述式中加圓括號。

<div class='goodcode'></div>

```python
Yes: if foo:
         bar()
     while x:
         x = bar()
     if x and y:
         bar()
     if not x:
         bar()
     # 單元素 tuple 使用 ()，在視覺上比逗號更明顯。
     onesie = (foo,)
     return foo
     return spam, beans
     return (spam, beans)
     for (x, y) in dict.items(): ...
```

<div class='badcode'></div>

```python
No:  if (x):
         bar()
     if not(x):
         bar()
     return (foo)
```

<a id="s3.4-indentation"></a>
<a id="34-indentation"></a>

<a id="indentation"></a>

### 3.4 縮排

程式碼區塊使用 *4 個空格*縮排。

不要使用 tab。隱含接續行應讓換行後的元素垂直對齊（參見[行長範例](#s3.2-line-length)），或使用 4 個空格的懸掛縮排。結尾的圓括號、方括號或大括號，可以放在運算式末端或獨立一行；若獨立一行，縮排應與包含對應起始括號的那一行相同。

<div class='goodcode'></div>

```python
Yes:   # 與起始分隔符號對齊。
       foo = long_function_name(var_one, var_two,
                                var_three, var_four)
       meal = (spam,
               beans)

       # 字典中與起始分隔符號對齊。
       foo = {
           'long_dictionary_key': value1 +
                                  value2,
           ...
       }

       # 4 個空格的懸掛縮排；第一行不放項目。
       foo = long_function_name(
           var_one, var_two, var_three,
           var_four)
       meal = (
           spam,
           beans)

       # 4 個空格的懸掛縮排；第一行不放項目，
       # 結尾圓括號獨立一行。
       foo = long_function_name(
           var_one, var_two, var_three,
           var_four
       )
       meal = (
           spam,
           beans,
       )

       # 字典中使用 4 個空格的懸掛縮排。
       foo = {
           'long_dictionary_key':
               long_dictionary_value,
           ...
       }
```

<div class='badcode'></div>

```python
No:    # 第一行不允許放項目。
       foo = long_function_name(var_one, var_two,
           var_three, var_four)
       meal = (spam,
           beans)

       # 不允許 2 個空格的懸掛縮排。
       foo = long_function_name(
         var_one, var_two, var_three,
         var_four)

       # 字典中缺少懸掛縮排。
       foo = {
           'long_dictionary_key':
           long_dictionary_value,
           ...
       }
```

<a id="s3.4.1-trailing-comma"></a>
<a id="s3.4.1-trailing-commas"></a>
<a id="s3.4.1-trailing_comma"></a>
<a id="s3.4.1-trailing_commas"></a>
<a id="341-trailing_comma"></a>
<a id="341-trailing_commas"></a>
<a id="trailing_comma"></a>
<a id="trailing_commas"></a>

<a id="trailing-comma"></a>

#### 3.4.1 項目序列中的尾端逗號？

只有當容器的結尾符號 `]`、`)` 或 `}` 不與最後一個元素同處一行，或 tuple 只有一個元素時，才建議保留尾端逗號。最後一個元素後的 `,` 也會提示 Python 自動格式化工具 [Black](https://github.com/psf/black) 或 [Pyink](https://github.com/google/pyink)，將容器格式化成每行一個項目。

<div class='goodcode'></div>

```python
Yes:   golomb3 = [0, 1, 3]
       golomb4 = [
           0,
           1,
           4,
           6,
       ]
```

<div class='badcode'></div>

```python
No:    golomb4 = [
           0,
           1,
           4,
           6,]
```

<a id="s3.5-blank-lines"></a>
<a id="35-blank-lines"></a>

<a id="blank-lines"></a>

### 3.5 空行

頂層定義之間空兩行，不論是函式或類別。方法定義之間，以及 `class` 的文件字串與第一個方法之間，空一行。`def` 那一行後面不空行。函式或方法內，可依判斷適當空一行。

空行不一定要緊鄰定義。例如，直接放在函式、類別或方法定義前的相關註解，也可能合理。請考慮該註解是否更適合寫進文件字串。

<a id="s3.6-whitespace"></a>
<a id="36-whitespace"></a>

<a id="whitespace"></a>

### 3.6 空白

標點符號周圍的空格，遵循標準排版規則。

圓括號、方括號或大括號內側不加空格。

<div class='goodcode'></div>

```python
Yes: spam(ham[1], {'eggs': 2}, [])
```

<div class='badcode'></div>

```python
No:  spam( ham[ 1 ], { 'eggs': 2 }, [ ] )
```

逗號、分號或冒號前不加空格；後面應加空格，除非位於行尾。

<div class='goodcode'></div>

```python
Yes: if x == 4:
         print(x, y)
     x, y = y, x
```

<div class='badcode'></div>

```python
No:  if x == 4 :
         print(x , y)
     x , y = y , x
```

引數串列、索引或切片的起始圓括號／方括號前，不加空格。

<div class='goodcode'></div>

```python
Yes: spam(1)
```

<div class='badcode'></div>

```python
No:  spam (1)
```

<div class='goodcode'></div>

```python
Yes: dict['key'] = list[index]
```

<div class='badcode'></div>

```python
No:  dict ['key'] = list [index]
```

行尾不留空白。

賦值（`=`）、比較（`==, <, >, !=, <>, <=, >=, in, not in, is, is not`）及布林（`and, or, not`）運算子，兩側各加一個空格。算術運算子（`+`、`-`、`*`、`/`、`//`、`%`、`**`、`@`）周圍的空格，請依判斷決定。

<div class='goodcode'></div>

```python
Yes: x == 1
```

<div class='badcode'></div>

```python
No:  x<1
```

傳入關鍵字引數或定義參數預設值時，`=` 兩側不加空格。唯一例外是[有型別註記時](#typing-default-values)，預設值的 `=` 兩側*應*加空格。

<div class='goodcode'></div>

```python
Yes: def complex(real, imag=0.0): return Magic(r=real, i=imag)
Yes: def complex(real, imag: float = 0.0): return Magic(r=real, i=imag)
```

<div class='badcode'></div>

```python
No:  def complex(real, imag = 0.0): return Magic(r = real, i = imag)
No:  def complex(real, imag: float=0.0): return Magic(r = real, i = imag)
```

不要用空格讓連續各行的符號垂直對齊，這會增加維護負擔；此規則適用於 `:`、`#`、`=` 等：

<div class='goodcode'></div>

```python
Yes:
  foo = 1000  # 註解
  long_name = 2  # 不應特意對齊的註解

  dictionary = {
      'foo': 1,
      'long_name': 2,
  }
```

<div class='badcode'></div>

```python
No:
  foo       = 1000  # 註解
  long_name = 2     # 不應特意對齊的註解

  dictionary = {
      'foo'      : 1,
      'long_name': 2,
  }
```

<a id="Python_Interpreter"></a>
<a id="s3.7-shebang-line"></a>
<a id="37-shebang-line"></a>

<a id="shebang-line"></a>

### 3.7 Shebang 行

大多數 `.py` 檔案不需要以 `#!` 開頭。依 [PEP-394](https://peps.python.org/pep-0394/)，程式主檔案應以 `#!/usr/bin/env python3`（支援 virtualenv）或 `#!/usr/bin/python3` 開頭。

這一行供核心尋找 Python 直譯器，Python 匯入模組時會忽略它。只有預計直接執行的檔案才需要。

<a id="s3.8-comments-and-docstrings"></a>
<a id="s3.8-comments"></a>
<a id="38-comments-and-docstrings"></a>

<a id="documentation"></a>

### 3.8 註解與文件字串

撰寫模組、函式、方法的文件字串及行內註解時，務必使用正確的風格。

<a id="s3.8.1-comments-in-doc-strings"></a>
<a id="381-docstrings"></a>
<a id="comments-in-doc-strings"></a>
<a id="docstrings"></a>

#### 3.8.1 文件字串

Python 使用「文件字串」（docstring）記錄程式碼的說明。文件字串是套件、模組、類別或函式中的第一個陳述式，且該陳述式是一個字串。這些字串可以透過物件的 `__doc__` 成員自動擷取，並由 `pydoc` 使用。（試著對自己的模組執行 `pydoc`，看看呈現結果。）文件字串一律使用三個雙引號 `"""` 的格式，依循 [PEP 257](https://peps.python.org/pep-0257/)。文件字串應以摘要行開頭：使用一個實體行，不超過 80 個字元，並以句號、問號或驚嘆號結尾。如果要撰寫更多內容（鼓勵這樣做），摘要行後面必須先空一行，再接續其餘內容；其餘內容的起始欄位應與第一行的第一個引號對齊。下文還有更多文件字串的格式指引。

<a id="s3.8.2-comments-in-modules"></a>
<a id="382-modules"></a>
<a id="comments-in-modules"></a>
<a id="module-docs"></a>

#### 3.8.2 模組

每個檔案都應包含授權聲明的制式文字。請依專案使用的授權選擇適當文字，例如 Apache 2.0、BSD、LGPL 或 GPL。

檔案開頭應有一段文件字串，說明模組的內容及使用方式。

<div class='goodcode'></div>

```python
"""用一行概述模組或程式，並以句號結尾。

空一行。文件字串的其餘部分應包含模組或程式的整體說明。
也可以選擇加入對外提供的類別與函式的簡短說明，及／或使用範例。

典型使用範例：

  foo = ClassFoo()
  bar = foo.function_bar()
"""
```

<a id="s3.8.2.1-test-modules"></a>
<a id="test-docs"></a>

##### 3.8.2.1 測試模組

測試模組不需要模組層級的文件字串。`unittest.TestCase` 的子類別不需要類別文件字串，其中以 `test_` 開頭的方法也不需要方法文件字串。只重複類別或方法名稱的文件字串應予省略。

如果文件字串能提供額外資訊，就應加入，例如具體說明如何執行測試，或解釋不尋常的設定方式或外部相依項目。

<div class='goodcode'></div>

```python
"""這個 blaze 測試使用 golden files。

你可以從 `google3` 目錄執行
`blaze run //foo/bar:foo_test -- --update_golden_files`
來更新這些檔案。
"""
```

不應使用未提供任何新資訊的文件字串。

<div class='badcode'></div>

```python
"""foo.bar 的測試。"""
```

或

<div class='badcode'></div>

```python
  def test_foo_is_barred(self):
    """測試 bar 是否套用到 foo。"""
```

<a id="s3.8.3-functions-and-methods"></a>
<a id="383-functions-and-methods"></a>
<a id="functions-and-methods"></a>
<a id="function-docs"></a>

#### 3.8.3 函式與方法

本節中的「函式」指方法、函式、產生器或屬性（property）。

任何符合下列一項或多項條件的函式，都必須有文件字串：

- 屬於公開 API。
- 規模並非微不足道。
- 邏輯並非一目瞭然。

文件字串應提供足夠資訊，讓人不必閱讀函式的程式碼就能撰寫呼叫。文件字串應說明函式的呼叫語法及語意，但通常不說明實作細節，除非這些細節與使用方式有關。例如，函式若會以副作用的形式修改某個引數，就應在文件字串中註明。至於與呼叫者無關、卻微妙而重要的實作細節，應以程式碼旁的註解說明，而非寫在函式的文件字串中。

文件字串可以採描述式（`"""從 Bigtable 擷取資料列。"""`，原文為 `"""Fetches rows from a Bigtable."""`），或祈使式（`"""請從 Bigtable 擷取資料列。"""`，原文為 `"""Fetch rows from a Bigtable."""`），但同一個檔案內應保持一致。`@property` 資料描述器的文件字串應採用與屬性或[函式引數](#doc-function-args)相同的風格（例如 `"""Bigtable 的路徑。"""`，而非 `"""回傳 Bigtable 的路徑。"""`）。

函式的某些面向應記錄在下列專用區段。每個區段以一個標題行開頭，並以冒號結尾。標題以外的內容應採用兩個或四個空格的懸掛縮排，同一個檔案內應保持一致。如果函式名稱與簽章已提供足夠資訊，能用單行文件字串妥善描述，就可以省略這些區段。

<a id="doc-function-args"></a>
[*Args:*](#doc-function-args)
:   依名稱列出每個參數。名稱後面應接說明，兩者之間以冒號加上一個空格或換行分隔。如果說明太長，無法放進不超過 80 個字元的單行，續行應比參數名稱多縮排兩個或四個空格，並與檔案中其他文件字串保持一致。如果程式碼沒有對應的型別註記，說明中應包含必要的型別資訊。如果函式接受 `*foo`（可變長度引數串列）及／或 `**bar`（任意關鍵字引數），應以 `*foo` 及 `**bar` 列出。

<a id="doc-function-returns"></a>
[*Returns:*（產生器則使用 *Yields:*）](#doc-function-returns)
:   描述回傳值的語意，包括型別註記未提供的型別資訊。如果函式只回傳 `None`，就不需要此區段。如果文件字串以「Return」、「Returns」、「Yield」或「Yields」開頭（例如 `"""將 Bigtable 的資料列以字串 tuple 回傳。"""`），且首句已足以描述回傳值，也可以省略。不要仿效舊版「NumPy 風格」（[範例](https://numpy.org/doc/1.24/reference/generated/numpy.linalg.qr.html)），將 tuple 回傳值寫得像是多個各自具名的回傳值，卻完全不提 tuple。應改為描述：「Returns: 一個 tuple (mat_a, mat_b)，其中 mat_a 是……，而……」。文件字串中輔助說明用的名稱，不一定要與函式本體中的內部名稱對應，因為內部名稱不是 API 的一部分。如果函式使用 `yield`，也就是產生器，`Yields:` 應記錄 `next()` 回傳的物件，而非呼叫該函式時得到的產生器物件本身。

<a id="doc-function-raises"></a>
[*Raises:*](#doc-function-raises)
:   列出所有與介面相關的例外，並附上說明。格式與 *Args:* 類似：例外名稱、冒號、空格或換行，以及懸掛縮排。不應記錄違反文件字串所定義的 API 時才會引發的例外，因為這樣會反過來將違反 API 時的行為也納入 API 的一部分。

<div class='goodcode'></div>

```python
def fetch_smalltable_rows(
    table_handle: smalltable.Table,
    keys: Sequence[bytes | str],
    require_all_keys: bool = False,
) -> Mapping[bytes, tuple[str, ...]]:
    """從 Smalltable 擷取資料列。

    從 table_handle 所代表的 Table 實例中，取得指定鍵值所對應的資料列。
    字串鍵值會以 UTF-8 編碼。

    Args:
        table_handle: 已開啟的 smalltable.Table 實例。
        keys: 字串序列，代表要擷取的各個資料列的鍵值。
          字串鍵值會以 UTF-8 編碼。
        require_all_keys: 若為 True，僅回傳所有鍵值均已設定值的資料列。

    Returns:
        將鍵值對應到所擷取資料列的 dict。
        每個資料列以字串 tuple 表示。例如：

        {b'Serak': ('Rigel VII', 'Preparer'),
         b'Zim': ('Irk', 'Invader'),
         b'Lrrr': ('Omicron Persei 8', 'Emperor')}

        回傳的鍵值一律為 bytes。如果 keys 引數中的某個鍵值不在字典中，
        就表示資料表中找不到該資料列，而且 require_all_keys 必定為 False。

    Raises:
        IOError: 存取 smalltable 時發生錯誤。
    """
```

同樣地，也允許下列在 `Args:` 中換行的變體：

<div class='goodcode'></div>

```python
def fetch_smalltable_rows(
    table_handle: smalltable.Table,
    keys: Sequence[bytes | str],
    require_all_keys: bool = False,
) -> Mapping[bytes, tuple[str, ...]]:
    """從 Smalltable 擷取資料列。

    從 table_handle 所代表的 Table 實例中，取得指定鍵值所對應的資料列。
    字串鍵值會以 UTF-8 編碼。

    Args:
      table_handle:
        已開啟的 smalltable.Table 實例。
      keys:
        字串序列，代表要擷取的各個資料列的鍵值。
        字串鍵值會以 UTF-8 編碼。
      require_all_keys:
        若為 True，僅回傳所有鍵值均已設定值的資料列。

    Returns:
      將鍵值對應到所擷取資料列的 dict。
      每個資料列以字串 tuple 表示。例如：

      {b'Serak': ('Rigel VII', 'Preparer'),
       b'Zim': ('Irk', 'Invader'),
       b'Lrrr': ('Omicron Persei 8', 'Emperor')}

      回傳的鍵值一律為 bytes。如果 keys 引數中的某個鍵值不在字典中，
      就表示資料表中找不到該資料列，而且 require_all_keys 必定為 False。

    Raises:
      IOError: 存取 smalltable 時發生錯誤。
    """
```

經過裝飾器處理的函式，其文件字串必須說明套用裝飾器後的行為，因為呼叫者觀察到的正是這個行為。

<div class='goodcode'></div>

```python
@contextlib.contextmanager
def read_from_remote_filesystem(url: str) -> Iterator[RemoteFile]:
    """開啟遠端檔案系統中的檔案以供讀取。

    Args:
      url: 遠端檔案的位址。

    Returns:
      提供遠端檔案參照的情境管理器。
    """
    reader = remote_file_reader(url)
    try:
        yield reader
    finally:
        reader.close()
```

<a id="s3.8.3.1-overridden-methods"></a>
<a id="overridden-method-docs"></a>

##### 3.8.3.1 覆寫的方法

覆寫基底類別方法的方法，若已明確加上 [`@override`](https://typing.python.org/en/latest/spec/class-compat.html#override) 裝飾器，就不需要文件字串。但如果覆寫後的行為實質上進一步限定了基底方法的契約，或有需要補充的細節（例如額外的副作用），則覆寫的方法仍須提供文件字串，至少說明這些差異。

<div class='goodcode'></div>

```python
from typing import override

class Parent:
  def do_something(self):
    """父類別的方法，包含文件字串。"""

# 子類別，其方法標註了 override。
class Child(Parent):
  @override
  def do_something(self):
    pass
```

<div class='badcode'></div>

```python
# 子類別未使用 @override 裝飾器，因此需要文件字串。
class Child(Parent):
  def do_something(self):
    pass

# 文件字串沒有提供額外資訊，@override 已足以表明可在基底類別找到文件。
class Child(Parent):
  @override
  def do_something(self):
    """請參閱基底類別。"""
```

<a id="s3.8.4-comments-in-classes"></a>
<a id="384-classes"></a>
<a id="comments-in-classes"></a>
<a id="class-docs"></a>

#### 3.8.4 類別

類別應在類別定義下方提供文件字串，描述該類別。公開屬性（不含 [property](#properties)）應記錄於此處的 `Attributes` 區段，並採用與[函式 `Args`](#doc-function-args) 區段相同的格式。

<div class='goodcode'></div>

```python
class SampleClass:
    """在此概述類別。

    更詳細的類別資訊……
    更詳細的類別資訊……

    Attributes:
        likes_spam: 布林值，表示我們是否喜歡 SPAM。
        eggs: 整數，表示我們已產下的蛋的數量。
    """

    def __init__(self, likes_spam: bool = False):
        """根據對 spam 的偏好初始化實例。

        Args:
          likes_spam: 定義實例是否具有這項偏好。
        """
        self.likes_spam = likes_spam
        self.eggs = 0

    @property
    def butter_sticks(self) -> int:
        """我們擁有的奶油條數量。"""
```

所有類別文件字串都應以單行摘要開頭，描述類別實例代表什麼。這表示 `Exception` 的子類別也應說明該例外代表什麼，而非它可能發生的情境。類別文件字串不應重複不必要的資訊，例如指出這個類別是一個類別。

<div class='goodcode'></div>

```python
# 正確：
class CheeseShopAddress:
  """起司店的地址。

  ...
  """

class OutOfCheeseError(Exception):
  """已無起司可供使用。"""
```

<div class='badcode'></div>

```python
# 錯誤：
class CheeseShopAddress:
  """描述起司店地址的類別。

  ...
  """

class OutOfCheeseError(Exception):
  """當沒有起司可供使用時引發。"""
```

如果類別使用了裝飾器，其文件字串必須說明套用裝飾器後的類別行為。

<a id="s3.8.5-block-and-inline-comments"></a>
<a id="comments-in-block-and-inline"></a>
<a id="s3.8.5-comments-in-block-and-inline"></a>
<a id="385-block-and-inline-comments"></a>
<a id="comments"></a>

#### 3.8.5 區塊註解與行內註解

最後一種需要註解的地方，是程式碼中難以理解的部分。如果你在下一次[程式碼審查](http://en.wikipedia.org/wiki/Code_review)時必須解釋它，就應現在加上註解。複雜操作應在操作開始前用幾行註解說明；不明顯的操作則在行尾加上註解。

<div class='goodcode'></div>

```python
# 我們使用加權字典搜尋，找出 i 在陣列中的位置。
# 根據陣列中的最大數值及陣列大小推估位置，
# 再透過二分搜尋找出確切數值。

if i & (i-1) == 0:  # 當 i 為 0 或 2 的冪次時為 True。
```

為了提高可讀性，這些註解的起始字元 `#` 應與程式碼至少相隔兩個空格，而 `#` 與註解文字之間至少相隔一個空格。

另一方面，不要只是描述程式碼。應假設閱讀者比你更熟悉 Python，只是不知道你想達成什麼。

<div class='badcode'></div>

```python
# 不好的註解：現在走訪 b 陣列，確保每當 i 出現時，
# 下一個元素都是 i+1。
```

<!-- 下一節複製自 C++ 風格指南。 -->

<a id="s3.8.6-punctuation-spelling-and-grammar"></a>
<a id="386-punctuation-spelling-and-grammar"></a>
<a id="spelling"></a>
<a id="punctuation"></a>
<a id="grammar"></a>
<a id="punctuation-spelling-grammar"></a>

#### 3.8.6 標點、拼字與文法

請注意標點、拼字與文法；寫得好的註解比寫得差的註解更容易閱讀。

註解應像敘述性文字一樣易讀，使用適當的大小寫及標點。許多情況下，完整句子比片段句更容易閱讀。較短的註解，例如程式碼行尾的註解，有時可以較不正式，但應保持風格一致。

程式碼審查者指出你應使用分號卻用了逗號，可能會讓人感到挫折，但讓原始碼維持高度清晰且易讀非常重要。正確的標點、拼字與文法有助於達成這個目標。

<a id="s3.10-strings"></a>
<a id="310-strings"></a>

<a id="strings"></a>

### 3.10 字串

格式化字串時，使用 [f-string](https://docs.python.org/3/reference/lexical_analysis.html#f-strings)、`%` 運算子或 `format` 方法，即使所有參數都是字串也一樣。請依判斷選擇方式。用 `+` 連接一次可以，但不要用 `+` 拼湊格式化內容。

<div class='goodcode'></div>

```python
Yes: x = f'name: {name}; score: {n}'
     x = '%s, %s!' % (imperative, expletive)
     x = '{}, {}'.format(first, second)
     x = 'name: %s; score: %d' % (name, n)
     x = 'name: %(name)s; score: %(score)d' % {'name':name, 'score':n}
     x = 'name: {}; score: {}'.format(name, n)
     x = a + b
```

<div class='badcode'></div>

```python
No: x = first + ', ' + second
    x = 'name: ' + name + '; score: ' + str(n)
```

避免在迴圈內用 `+` 或 `+=` 累積字串。某些情況下，字串相加會使執行時間由線性變成平方成長。雖然 CPython 可能最佳化這類常見累積方式，但那是實作細節；最佳化成立的條件不易預測，也可能改變。應將每個子字串加入串列，迴圈結束後用 `''.join` 合併，或將子字串寫入 `io.StringIO` 緩衝區。這些方式具有穩定的攤銷線性時間複雜度。

<div class='goodcode'></div>

```python
Yes: items = ['<table>']
     for last_name, first_name in employee_list:
         items.append('<tr><td>%s, %s</td></tr>' % (last_name, first_name))
     items.append('</table>')
     employee_table = ''.join(items)
```

<div class='badcode'></div>

```python
No: employee_table = '<table>'
    for last_name, first_name in employee_list:
        employee_table += '<tr><td>%s, %s</td></tr>' % (last_name, first_name)
    employee_table += '</table>'
```

同一檔案中應一致使用字串引號：選擇 `'` 或 `"` 並持續使用。若能避免在字串內用反斜線跳脫引號，則可以改用另一種引號。

<div class='goodcode'></div>

```python
Yes:
  Python('Why are you hiding your eyes?')
  Gollum("I'm scared of lint errors.")
  Narrator('"Good!" thought a happy Python reviewer.')
```

<div class='badcode'></div>

```python
No:
  Python("Why are you hiding your eyes?")
  Gollum('The lint. It burns. It burns us.')
  Gollum("Always the great lint. Watching. Watching.")
```

多行字串優先使用 `"""` 而非 `'''`。只有當專案的一般字串也使用 `'` 時，才能選擇讓所有非文件字串的多行字串使用 `'''`。文件字串一律必須使用 `"""`。

多行字串不會自動配合程式其餘部分的縮排。若需避免字串中包含額外空格，可串接多個單行字串，或對多行字串使用 [`textwrap.dedent()`](https://docs.python.org/3/library/textwrap.html#textwrap.dedent)，移除每行開頭的空白：

<div class='badcode'></div>

```python
  No:
  long_string = """This is pretty ugly.
Don't do this.
"""
```

<div class='goodcode'></div>

```python
  Yes:
  long_string = """This is fine if your use case can accept
      extraneous leading spaces."""
```

<div class='goodcode'></div>

```python
  Yes:
  long_string = ("And this is fine if you cannot accept\n" +
                 "extraneous leading spaces.")
```

<div class='goodcode'></div>

```python
  Yes:
  long_string = ("And this too is fine if you cannot accept\n"
                 "extraneous leading spaces.")
```

<div class='goodcode'></div>

```python
  Yes:
  import textwrap

  long_string = textwrap.dedent("""\
      This is also fine, because textwrap.dedent()
      will collapse common leading spaces in each line.""")
```

注意，這裡使用反斜線並未違反禁止[明確接續行](#line-length)的規則；此處是在字串常值內[跳脫換行](https://docs.python.org/3/reference/lexical_analysis.html#string-and-bytes-literals)。

<a id="s3.10.1-logging"></a>
<a id="3101-logging"></a>
<a id="logging"></a>

<a id="logging"></a>

#### 3.10.1 日誌

對於以格式字串（含 `%` 佔位符）為第一個引數的日誌函式：第一個引數一律傳入字串常值，而非 f-string；格式參數放在後續引數。某些日誌實作會保留尚未展開的格式字串，作為可查詢欄位。這也能避免在沒有任何 logger 會輸出該訊息時，仍耗費時間組合訊息。

<div class='goodcode'></div>

```python
  Yes:
  import tensorflow as tf
  logger = tf.get_logger()
  logger.info('TensorFlow Version is: %s', tf.__version__)
```

<div class='goodcode'></div>

```python
  Yes:
  import os
  from absl import logging

  logging.info('Current $PAGER is: %s', os.getenv('PAGER', default=''))

  homedir = os.getenv('HOME')
  if homedir is None or not os.access(homedir, os.W_OK):
    logging.error('Cannot write to home directory, $HOME=%r', homedir)
```

<div class='badcode'></div>

```python
  No:
  import os
  from absl import logging

  logging.info('Current $PAGER is:')
  logging.info(os.getenv('PAGER', default=''))

  homedir = os.getenv('HOME')
  if homedir is None or not os.access(homedir, os.W_OK):
    logging.error(f'Cannot write to home directory, $HOME={homedir!r}')
```

<a id="s3.10.2-error-messages"></a>
<a id="3102-error-messages"></a>
<a id="error-messages"></a>

<a id="error-messages"></a>

#### 3.10.2 錯誤訊息

錯誤訊息，例如 `ValueError` 等例外中的訊息字串，或顯示給使用者的訊息，應遵循三項指引：

1.  訊息必須精確對應實際錯誤情況。

2.  插入的內容必須能清楚辨識。

3.  應便於簡單的自動化處理，例如用 grep 搜尋。

<div class='goodcode'></div>

```python
  Yes:
  if not 0 <= p <= 1:
    raise ValueError(f'Not a probability: {p=}')

  try:
    os.rmdir(workdir)
  except OSError as error:
    logging.warning('Could not remove directory (reason: %r): %r',
                    error, workdir)
```

<div class='badcode'></div>

```python
  No:
  if p < 0 or p > 1:  # 問題：對 float('nan') 也會是 False！
    raise ValueError(f'Not a probability: {p=}')

  try:
    os.rmdir(workdir)
  except OSError:
    # 問題：訊息做出可能不成立的假設：
    # 刪除可能因其他原因失敗，會誤導
    # 負責除錯的人。
    logging.warning('Directory already was deleted: %s', workdir)

  try:
    os.rmdir(workdir)
  except OSError:
    # 問題：訊息不必要地增加 grep 搜尋難度，
    # 且對 `workdir` 的某些值會造成混淆。
    # 想像有人呼叫包含這段程式碼的函式庫函式，
    # 使用 workdir = 'deleted' 之類的名稱，警告就會變成：
    # "The deleted directory could not be deleted."（deleted 目錄無法刪除。）
    logging.warning('The %s directory could not be deleted.', workdir)
```

<a id="s3.11-files-sockets-closeables"></a>
<a id="s3.11-files-and-sockets"></a>
<a id="311-files-and-sockets"></a>
<a id="files-and-sockets"></a>

<a id="files"></a>

### 3.11 檔案、Socket 與類似的有狀態資源

使用完畢後，明確關閉檔案與 socket。這條規則自然延伸到內部使用 socket 的可關閉資源，例如資料庫連線，以及其他需要以類似方式關閉的資源。例子包括 [mmap](https://docs.python.org/3/library/mmap.html) 映射、[h5py File 物件](https://docs.h5py.org/en/stable/high/file.html)，以及 [matplotlib.pyplot 圖形視窗](https://matplotlib.org/2.1.0/api/_as_gen/matplotlib.pyplot.close.html)。

不必要地讓檔案、socket 或其他有狀態物件保持開啟，有許多缺點：

-   可能占用有限的系統資源，例如檔案描述元。處理大量這類物件的程式碼，若未在使用後及時歸還資源，可能不必要地耗盡資源。
-   保持檔案開啟可能阻止其他操作，例如移動、刪除檔案或卸載檔案系統。
-   程式中共用的檔案與 socket，可能在邏輯上已關閉後仍被誤讀或誤寫。若真的關閉它們，讀寫嘗試便會引發例外，讓問題更早被發現。

此外，雖然檔案、socket 及部分行為相似的資源，在物件銷毀時會自動關閉，但將物件生命週期與資源狀態耦合並非好做法：

-   無法保證執行環境何時會真正呼叫 `__del__` 方法。不同 Python 實作採用不同記憶體管理技術，例如延遲垃圾回收，可能任意且無限期延長物件生命週期。
-   非預期的檔案參照，例如全域變數或例外的 traceback，可能讓檔案比預期存留更久。

依賴終結器自動清理具有可觀察副作用的資源，數十年來已在多種語言中反覆證實會造成重大問題，例如這篇 [Java 文章](https://wiki.sei.cmu.edu/confluence/display/java/MET12-J.+Do+not+use+finalizers)。

管理檔案及類似資源的首選方式，是使用 [`with` 陳述式](http://docs.python.org/reference/compound_stmts.html#the-with-statement)：

<div class='goodcode'></div>

```python
with open("hello.txt") as hello_file:
    for line in hello_file:
        print(line)
```

不支援 `with` 陳述式的類檔案物件，使用 `contextlib.closing()`：

<div class='goodcode'></div>

```python
import contextlib

with contextlib.closing(urllib.urlopen("http://www.python.org/")) as front_page:
    for line in front_page:
        print(line)
```

極少數無法使用情境式資源管理的情況下，程式文件必須明確解釋如何管理資源生命週期。

<a id="s3.12-todo-comments"></a>
<a id="312-todo-comments"></a>

<a id="todo"></a>

### 3.12 TODO 註解

對暫時性程式碼、短期解法，或已足夠好但尚未完善的程式碼，使用 `TODO` 註解。

`TODO` 註解以全大寫的 `TODO` 開頭，後接括號括住的背景資訊資源連結，最好是問題追蹤連結，因為問題會被追蹤，也有後續討論。這段背景資訊後接冒號與說明文字。

目的是維持一致且可搜尋的 `TODO` 格式，讓人知道如何取得更多細節。

<div class='goodcode'></div>

```python
# TODO(example.com/12345): 研究 cpufreq 最佳化。
```

下列是過去建議、但已不鼓勵新程式碼使用的舊格式：

```python
# TODO: example.com/12345 - 研究 cpufreq 最佳化。
```

避免在 TODO 中以個人或團隊作為背景資訊：

<div class='badcode'></div>

```python
# TODO(username): 建立問題追蹤項目，並使用 '*' 表示重複。
```

如果 `TODO` 是「未來某個時間做某事」，務必寫出未來維護者能理解的明確日期，例如「2009 年 11 月前修正」，或明確事件，例如「當所有用戶端都能處理 XML 回應時移除此程式碼」。問題追蹤系統很適合追蹤這類工作。

<a id="s3.13-imports-formatting"></a>
<a id="313-imports-formatting"></a>

<a id="imports-formatting"></a>

### 3.13 匯入格式

各項匯入應分行撰寫；[`typing` 與 `collections.abc` 的匯入有例外](#typing-imports)。

例如：

<div class='goodcode'></div>

```python
Yes: from collections.abc import Mapping, Sequence
     import os
     import sys
     from typing import Any, NewType
```

<div class='badcode'></div>

```python
No:  import os, sys
```

匯入一律放在檔案頂部，位於模組註解與文件字串之後、模組全域變數與常數之前。匯入應由最通用到最專用分組：

1.  Python future 匯入陳述式。例如：

    <div class='goodcode'></div>

    ```python
    from __future__ import annotations
    ```

    更多資訊見[上文](#from-future-imports)。

2.  Python 標準函式庫匯入。例如：

    <div class='goodcode'></div>

    ```python
    import sys
    ```

3.  [第三方](https://pypi.org/)模組或套件匯入。例如：

    <div class='goodcode'></div>

    ```python
    import tensorflow as tf
    ```

4.  程式碼儲存庫中的子套件匯入。例如：

    <div class='goodcode'></div>

    ```python
    from otherproject.ai import mind
    ```

5.  **已棄用：**與目前檔案位於同一頂層子套件的應用程式專用匯入。例如：

    <div class='goodcode'></div>

    ```python
    from myproject.backend.hgwells import time_machine
    ```

    舊版 Google Python 風格程式碼可能採取這種做法，但已不再要求。**新程式碼不必特別這樣區分。**將應用程式專用的子套件匯入視為一般子套件匯入即可。

每組內應依模組的完整套件路徑（`from path import ...` 中的 `path`），忽略大小寫，以字典順序排序。可以選擇在各匯入區段之間空一行。

<div class='goodcode'></div>

```python
import collections
import queue
import sys

from absl import app
from absl import flags
import bs4
import cryptography
import tensorflow as tf

from book.genres import scifi
from myproject.backend import huxley
from myproject.backend.hgwells import time_machine
from myproject.backend.state_machine import main_loop
from otherproject.ai import body
from otherproject.ai import mind
from otherproject.ai import soul

# 舊風格程式碼可能改將下列匯入放在這裡：
#from myproject.backend.hgwells import time_machine
#from myproject.backend.state_machine import main_loop
```

<a id="s3.14-statements"></a>
<a id="314-statements"></a>

<a id="statements"></a>

### 3.14 陳述式

一般情況下，每行只放一個陳述式。

只有當完整陳述式能放在單行時，才可以把條件判斷及其執行內容放在同一行。尤其 `try`／`except` 絕不可這樣寫，因為兩者無法同處一行；`if` 則只有在沒有 `else` 時才可以。

<div class='goodcode'></div>

```python
Yes:

  if foo: bar(foo)
```

<div class='badcode'></div>

```python
No:

  if foo: bar(foo)
  else:   baz(foo)

  try:               bar(foo)
  except ValueError: baz(foo)

  try:
      bar(foo)
  except ValueError: baz(foo)
```

<a id="s3.15-accessors"></a>
<a id="s3.15-access-control"></a>
<a id="315-access-control"></a>
<a id="access-control"></a>
<a id="accessors"></a>

<a id="getters-and-setters"></a>

### 3.15 Getter 與 Setter

Getter 與 setter 函式，也稱 accessor 與 mutator，應在它們對讀取或設定變數值具有實質作用或行為時使用。

特別是讀取或設定變數目前已很複雜、成本很高，或合理預期未來會如此時，應使用這些函式。

例如，一對 getter／setter 若只是讀寫內部屬性，應直接公開該屬性。相較之下，如果設定變數會使某些狀態失效或重建，就應使用 setter 函式；函式呼叫提示可能正在進行不簡單的操作。若只需要簡單邏輯，也可考慮 [property](#properties)，或重構成不再需要 getter 與 setter。

Getter 與 setter 應遵循[命名](#s3.16-naming)指引，例如 `get_foo()` 及 `set_foo()`。

如果過去允許透過 property 存取，不要將新的 getter／setter 函式綁回該 property。仍試圖使用舊方式存取的程式碼，應明確失敗，讓使用者知道操作複雜度已改變。

<a id="s3.16-naming"></a>
<a id="316-naming"></a>

<a id="naming"></a>

### 3.16 命名

`module_name`、`package_name`、`ClassName`、`method_name`、`ExceptionName`、`function_name`、`GLOBAL_CONSTANT_NAME`、`global_var_name`、`instance_var_name`、`function_parameter_name`、`local_var_name`、`query_proper_noun_for_thing`、`send_acronym_via_https`。

名稱應具描述性，包含函式、類別、變數、屬性、檔案及任何其他具名實體。

避免縮寫。尤其不要使用對專案外讀者而言含糊或陌生的縮寫，也不要刪掉單字中間的字母來縮寫。

檔名一律使用 `.py` 副檔名，絕不使用連字號。

<a id="s3.16.1-names-to-avoid"></a>
<a id="3161-names-to-avoid"></a>

<a id="names-to-avoid"></a>

#### 3.16.1 應避免的名稱

-   單一字元名稱，除非屬於下列明確允許的情況：

    -   計數器或迭代器，例如 `i`、`j`、`k`、`v` 等。
    -   `try/except` 陳述式中的例外識別字 `e`。
    -   `with` 陳述式中的檔案控制代碼 `f`。
    -   沒有約束的私有[型別變數](#typing-type-var)，例如 `_T = TypeVar("_T")`、`_P = ParamSpec("_P")`。
    -   與參考論文或演算法中的既定符號一致的名稱，參見[數學符號](#math-notation)。

    請勿濫用單字元命名。一般而言，描述程度應與名稱的可見範圍成正比。例如，`i` 在五行程式碼區塊中可能合適，但在多層巢狀作用域中可能過於模糊。

-   套件／模組名稱中的連字號（`-`）。

-   `__double_leading_and_trailing_underscore__` 形式的名稱，這是 Python 保留的命名方式。

-   冒犯性詞彙。

-   不必要地包含變數型別的名稱，例如 `id_to_name_dict`。

<a id="s3.16.2-naming-conventions"></a>
<a id="3162-naming-convention"></a>

<a id="naming-conventions"></a>

#### 3.16.2 命名慣例

-   一般而言，遵循 [PEP 8 命名慣例][PEP-8-naming-conventions]。

-   「內部」指模組內部，或類別中的受保護、私有成員。

-   名稱前加單底線（`_`）能在一定程度上保護模組變數與函式，lint 工具會標示對受保護成員的存取。注意，單元測試可以存取受測模組中的受保護常數。

-   在實例變數或方法前加雙底線（`__`，也稱 dunder），會透過名稱改寫，使它實質上成為所屬類別的私有成員。我們不鼓勵使用，因為它影響可讀性與可測試性，而且並非*真正*私有。應優先使用單底線。

-   將相關類別與頂層函式放在同一模組。與 Java 不同，不必限制每個模組只能有一個類別。

-   類別名稱使用 CapWords，模組名稱則用 lower\_with\_under.py。雖然有些舊模組名為 CapWords.py，但現在已不鼓勵，因為當模組恰好與類別同名時會造成混淆：「等等，我寫的是 `import StringIO`，還是 `from StringIO import StringIO`？」

    -   注意，[PEP 8 指出][PEP-8-acronyms]：「在 CapWords 中使用縮寫時，縮寫的每個字母都應大寫。因此 HTTPServerError 比 HttpServerError 更好。」

-   新的*單元測試*檔案，方法名稱應遵循 PEP 8 的 lower\_with\_under 格式，例如 `test_<method_under_test>_<state>`。為與採用 CapWords 函式名稱的舊模組保持一致（\*），以 `test` 開頭的方法名稱可以用底線區分邏輯部分，例如 `test<MethodUnderTest>_<state>`。

[PEP-8-naming-conventions]: https://peps.python.org/pep-0008/#naming-conventions
[PEP-8-acronyms]: https://peps.python.org/pep-0008/#descriptive-naming-styles

<a id="naming-exemptions"></a>

##### 3.16.2.1 例外

上述一般命名慣例有下列例外：

-   Python 程式碼若與外部或非 Python 程式碼緊密耦合，例如對 C++ 的外部函式介面（FFI），為了與其他程式碼保持一致，可以採用不同慣例，參見[一致性](#consistency)。

<a id="s3.16.3-file-naming"></a>
<a id="3163-file-naming"></a>

<a id="file-naming"></a>

#### 3.16.3 檔案命名

Python 檔名必須有 `.py` 副檔名，且不得包含連字號（`-`），才能被匯入與進行單元測試。如果希望執行檔在不帶副檔名時也能使用，應建立符號連結，或使用包含 `exec "$0.py" "$@"` 的簡單 bash 包裝程式。

<a id="s3.16.4-guidelines-derived-from-guidos-recommendations"></a>
<a id="3164-guidelines-derived-from-guidos-recommendations"></a>

<a id="guidelines-derived-from-guidos-recommendations"></a>

#### 3.16.4 依 [Guido](https://en.wikipedia.org/wiki/Guido_van_Rossum) 建議衍生的指引

<table rules="all" border="1" summary="Guidelines from Guido 的建議"
       cellspacing="2" cellpadding="2">

  <tr>
    <th>種類</th>
    <th>公開</th>
    <th>內部</th>
  </tr>

  <tr>
    <td>套件</td>
    <td><code>lower_with_under</code></td>
    <td></td>
  </tr>

  <tr>
    <td>模組</td>
    <td><code>lower_with_under</code></td>
    <td><code>_lower_with_under</code></td>
  </tr>

  <tr>
    <td>類別</td>
    <td><code>CapWords</code></td>
    <td><code>_CapWords</code></td>
  </tr>

  <tr>
    <td>例外</td>
    <td><code>CapWords</code></td>
    <td></td>
  </tr>

  <tr>
    <td>函式</td>
    <td><code>lower_with_under()</code></td>
    <td><code>_lower_with_under()</code></td>
  </tr>

  <tr>
    <td>全域／類別常數</td>
    <td><code>CAPS_WITH_UNDER</code></td>
    <td><code>_CAPS_WITH_UNDER</code></td>
  </tr>

  <tr>
    <td>全域／類別變數</td>
    <td><code>lower_with_under</code></td>
    <td><code>_lower_with_under</code></td>
  </tr>

  <tr>
    <td>實例變數</td>
    <td><code>lower_with_under</code></td>
    <td><code>_lower_with_under</code> （受保護）</td>
  </tr>

  <tr>
    <td>方法名稱</td>
    <td><code>lower_with_under()</code></td>
    <td><code>_lower_with_under()</code> （受保護）</td>
  </tr>

  <tr>
    <td>函式／方法參數</td>
    <td><code>lower_with_under</code></td>
    <td></td>
  </tr>

  <tr>
    <td>區域變數</td>
    <td><code>lower_with_under</code></td>
    <td></td>
  </tr>

</table>

<a id="s3.17-main"></a>
<a id="317-main"></a>

<a id="math-notation"></a>

#### 3.16.5 數學符號

對於大量數學運算的程式碼，如果短變數名稱符合參考論文或演算法中的既定符號，即使原本會違反本指南，也應優先採用。

使用基於既定符號的名稱時：

1.  在註解或文件字串中引用所有命名慣例的來源，最好以超連結指向學術資源本身。若無法存取來源，應清楚記錄命名慣例。
2.  公開 API 優先使用符合 PEP 8 的 `descriptive_names`，因為它們更可能在缺乏上下文的情況下被閱讀。
3.  以範圍盡可能小的 `pylint: disable=invalid-name` 指令停用警告。只有少數變數時，逐一放在各行行尾註解；較多時，放在區塊開頭。

<a id="main"></a>

### 3.17 主程式

在 Python 中，`pydoc` 與單元測試都需要模組可以被匯入。若檔案預計作為執行檔，其主要功能應放在 `main()` 函式中；執行主程式前，一律檢查 `if __name__ == '__main__'`，避免模組匯入時執行主程式。

使用 [absl](https://github.com/abseil/abseil-py) 時，使用 `app.run`：

<div class='goodcode'></div>

```python
from absl import app
...

def main(argv: Sequence[str]):
    # 處理非旗標引數
    ...

if __name__ == '__main__':
    app.run(main)
```

其他情況使用：

<div class='goodcode'></div>

```python
def main():
    ...

if __name__ == '__main__':
    main()
```

所有頂層程式碼都會在模組匯入時執行。注意不要呼叫函式、建立物件，或執行其他不應在 `pydoc` 處理檔案時發生的操作。

<a id="s3.18-function-length"></a>
<a id="318-function-length"></a>

<a id="function-length"></a>

### 3.18 函式長度

優先撰寫小而專注的函式。

我們理解長函式有時是適當的，因此不對函式長度設硬性限制。若函式超過約 40 行，請思考能否在不破壞程式結構的前提下拆分。

即使長函式現在運作完美，幾個月後修改的人可能加入新行為，造成難以發現的錯誤。保持函式簡短、單純，有助於其他人閱讀與修改。

處理程式碼時，可能遇到又長又複雜的函式。不要害怕修改既有程式碼：如果難以處理、錯誤難以除錯，或想在多個不同情境重用其中一部分，應考慮拆成更小、更容易管理的部分。

<a id="s3.19-type-annotations"></a>
<a id="319-type-annotations"></a>

<a id="type-annotations"></a>

### 3.19 型別註記

<a id="s3.19.1-general-rules"></a>
<a id="s3.19.1-general"></a>
<a id="3191-general-rules"></a>

<a id="typing-general"></a>

#### 3.19.1 一般規則

*   熟悉[型別提示](https://docs.python.org/3/library/typing.html)。

*   通常不必標註 `self` 或 `cls`。若正確表達型別資訊有需要，可以使用 [`Self`](https://docs.python.org/3/library/typing.html#typing.Self)，例如：

    <div class='goodcode'></div>

    ```python
    from typing import Self

    class BaseClass:
      @classmethod
      def create(cls) -> Self:
        ...

      def difference(self, other: Self) -> float:
        ...
    ```

*   同樣地，不必強求標註 `__init__` 的回傳值，因為 `None` 是唯一合法選項。

*   若不應明確表達其他變數或回傳值的型別，使用 `Any`。

*   不要求為模組中所有函式都加入註記。

    -   至少標註公開 API。
    -   運用判斷，在安全性、清晰度與靈活性之間取得平衡。
    -   標註容易出現型別錯誤的程式碼，例如曾有相關錯誤或較複雜的部分。
    -   標註難以理解的程式碼。
    -   當程式碼的型別逐漸穩定時加入註記。許多情況下，成熟程式碼中的所有函式都可以標註，而不會犧牲太多靈活性。

<a id="s3.19.2-line-breaking"></a>
<a id="3192-line-breaking"></a>

<a id="typing-line-breaking"></a>

#### 3.19.2 換行

盡量遵循既有[縮排](#indentation)規則。

加入註記後，許多函式簽章會變成「每行一個參數」。為確保回傳型別也獨立一行，可以在最後一個參數後加逗號。

<div class='goodcode'></div>

```python
def my_method(
    self,
    first_var: int,
    second_var: Foo,
    third_var: Bar | None,
) -> int:
  ...
```

一律優先在變數之間換行，而非在變數名稱與型別註記之間換行。不過，若所有內容能放在同一行，就放在同一行。

<div class='goodcode'></div>

```python
def my_method(self, first_var: int) -> int:
  ...
```

若函式名稱、最後一個參數與回傳型別的組合太長，應另起一行並縮排 4 個空格。換行時，優先讓每個參數與回傳型別各占一行，並讓結尾圓括號與 `def` 對齊：

<div class='goodcode'></div>

```python
Yes:
def my_method(
    self,
    other_arg: MyLongType | None,
) -> tuple[MyLongType1, MyLongType1]:
  ...
```

也可以選擇將回傳型別放在最後一個參數的同一行：

<div class='goodcode'></div>

```python
Okay:
def my_method(
    self,
    first_var: int,
    second_var: int) -> dict[OtherLongType, MyLongType]:
  ...
```

`pylint` 允許將結尾圓括號移到新的一行，並與起始圓括號對齊，但這樣可讀性較差。

<div class='badcode'></div>

```python
No:
def my_method(self,
              other_arg: MyLongType | None,
             ) -> dict[OtherLongType, MyLongType]:
  ...
```

如上述範例，應盡量避免拆開型別。但有時型別太長，無法放在同一行；此時盡量不要拆開子型別。

<div class='goodcode'></div>

```python
def my_method(
    self,
    first_var: tuple[list[MyLongType1],
                     list[MyLongType2]],
    second_var: list[dict[
        MyLongType3, MyLongType4]],
) -> None:
  ...
```

若單一名稱與型別仍太長，考慮為型別建立[別名](#typing-aliases)。最後手段才是在冒號後換行，並縮排 4 個空格。

<div class='goodcode'></div>

```python
Yes:
def my_function(
    long_variable_name:
        long_module_name.LongTypeName,
) -> None:
  ...
```

<div class='badcode'></div>

```python
No:
def my_function(
    long_variable_name: long_module_name.
        LongTypeName,
) -> None:
  ...
```

<a id="s3.19.3-forward-declarations"></a>
<a id="3193-forward-declarations"></a>

<a id="forward-declarations"></a>

#### 3.19.3 前向宣告

如果需要使用同一模組中尚未定義的類別名稱，例如在類別自身的宣告內使用，或使用稍後才定義的類別，應使用 `from __future__ import annotations`，或以字串表示類別名稱。

<div class='goodcode'></div>

```python
Yes:
from __future__ import annotations

class MyClass:
  def __init__(self, stack: Sequence[MyClass], item: OtherClass) -> None:

class OtherClass:
  ...
```

<div class='goodcode'></div>

```python
Yes:
class MyClass:
  def __init__(self, stack: Sequence['MyClass'], item: 'OtherClass') -> None:

class OtherClass:
  ...
```

<a id="s3.19.4-default-values"></a>
<a id="3194-default-values"></a>

<a id="typing-default-values"></a>

#### 3.19.4 預設值

依 [PEP-008](https://peps.python.org/pep-0008/#other-recommendations)，*只有*同時具有型別註記與預設值的引數，才在 `=` 兩側加空格。

<div class='goodcode'></div>

```python
Yes:
def func(a: int = 0) -> int:
  ...
```

<div class='badcode'></div>

```python
No:
def func(a:int=0) -> int:
  ...
```

<a id="s3.19.5-nonetype"></a>
<a id="s3.19.5-none-type"></a>
<a id="3195-nonetype"></a>

<a id="none-type"></a>

#### 3.19.5 NoneType

在 Python 型別系統中，`NoneType` 是「一等」型別；就型別標註而言，`None` 是 `NoneType` 的別名。引數若可以是 `None`，就必須明確宣告！可以使用 `|` 聯集型別運算式（新的 Python 3.10+ 程式碼建議使用），或較舊的 `Optional` 與 `Union` 語法。

明確使用 `X | None`，不要依賴隱含行為。舊版型別檢查器允許將 `a: str = None` 解讀為 `a: str | None = None`，但現在已不建議這種行為。

<div class='goodcode'></div>

```python
Yes:
def modern_or_union(a: str | int | None, b: str | None = None) -> str:
  ...
def union_optional(a: Union[str, int, None], b: Optional[str] = None) -> str:
  ...
```

<div class='badcode'></div>

```python
No:
def nullable_union(a: Union[None, str]) -> str:
  ...
def implicit_optional(a: str = None) -> str:
  ...
```

<a id="s3.19.6-type-aliases"></a>
<a id="s3.19.6-aliases"></a>
<a id="3196-type-aliases"></a>
<a id="typing-aliases"></a>

<a id="type-aliases"></a>

#### 3.19.6 型別別名

可以為複雜型別宣告別名。

*   別名應以 CapWords 命名。僅供目前模組使用時，應採用 \_Private 形式。
*   別名應以 `typing.TypeAlias` 標註，以區別於不是型別的全域變數。
*   不要用型別別名取代 `from module import symbol` 寫法；後者[不被允許](#imports)。

<div class='goodcode'></div>

```python
Yes:
from typing import TypeAlias

_LossAndGradient: TypeAlias = tuple[tf.Tensor, tf.Tensor]
ComplexTFMap: TypeAlias = Mapping[str, _LossAndGradient]
```

<div class='badcode'></div>

```python
No:
import immutabledict

immutabledict = immutabledict.immutabledict
```

```python
# 為了方便可以這樣寫，但前提是別名不出現在本模組的公開 API 中，
# 例如公開函式的簽章。
_ShortName: TypeAlias = other_module.SignificantlyInconvenientlyLongName
```

<a id="s3.19.7-ignoring-types"></a>
<a id="s3.19.7-ignore"></a>
<a id="3197-ignoring-types"></a>

<a id="typing-ignore"></a>

#### 3.19.7 忽略型別檢查

可以用特殊註解 `# type: ignore`，停用某一行的型別檢查。

`pyrefly` 提供停用特定錯誤的選項，類似 lint：

<div class='goodcode'></div>

```python
# pyrefly: ignore[attribute-error]
```

<a id="s3.19.8-typing-variables"></a>
<a id="s3.19.8-comments"></a>
<a id="3198-typing-internal-variables"></a>

<a id="typing-variables"></a>

#### 3.19.8 變數的型別標註

<a id="annotated-assignments"></a>
[*帶註記的賦值*](#annotated-assignments)
:   若內部變數的型別難以或無法推斷，應以帶註記的賦值指定型別：在變數名稱與值之間放冒號與型別，與具有預設值的函式引數寫法相同：

    <div class='goodcode'></div>

    ```python
    a: Foo = SomeUndecoratedFunction()
    ```

<a id="type-comments"></a>
[*型別註解*](#type-comments)
:   雖然程式碼中可能仍有這種寫法，因為 Python 3.6 以前需要，但不要再新增行尾的 `# type: <type name>` 註解：

    <div class='badcode'></div>

    ```python
    a = SomeUndecoratedFunction()  # type: Foo
    ```

<a id="s3.19.9-tuples-vs-lists"></a>
<a id="s3.19.9-tuples"></a>
<a id="3199-tuples-vs-lists"></a>

<a id="typing-tuples"></a>

#### 3.19.9 Tuple 與串列

具型別註記的串列只能包含單一型別的物件。具型別註記的 tuple 可以是同一型別重複出現，也可以是固定數量、各自不同型別的元素。後者常用於函式回傳型別。

<div class='goodcode'></div>

```python
a: list[int] = [1, 2, 3]
b: tuple[int, ...] = (1, 2, 3)
c: tuple[int, str, float] = (1, "2", 3.5)
```

<a id="s3.19.10-typevars"></a>
<a id="s3.19.10-type-var"></a>
<a id="31910-typevar"></a>
<a id="typing-type-var"></a>

<a id="typevars"></a>

#### 3.19.10 型別變數

Python 型別系統支援[泛型](https://docs.python.org/3/library/typing.html#generics)。`TypeVar`、`ParamSpec` 等型別變數是使用泛型的常見方式。

範例：

<div class='goodcode'></div>

```python
from collections.abc import Callable
from typing import ParamSpec, TypeVar
_P = ParamSpec("_P")
_T = TypeVar("_T")
...
def next(l: list[_T]) -> _T:
  return l.pop()

def print_when_called(f: Callable[_P, _T]) -> Callable[_P, _T]:
  def inner(*args: _P.args, **kwargs: _P.kwargs) -> _T:
    print("Function was called")
    return f(*args, **kwargs)
  return inner
```

`TypeVar` 可以加上約束：

<div class='goodcode'></div>

```python
AddableType = TypeVar("AddableType", int, float, str)
def add(a: AddableType, b: AddableType) -> AddableType:
  return a + b
```

`typing` 模組中常見的預定義型別變數是 `AnyStr`。如果多個註記都可以是 `bytes` 或 `str`，且必須全部為相同型別，就使用它。

<div class='goodcode'></div>

```python
from typing import AnyStr
def check_length(x: AnyStr) -> AnyStr:
  if len(x) <= 42:
    return x
  raise ValueError()
```

型別變數必須有描述性名稱，除非同時符合下列所有條件：

*   對外不可見。
*   沒有約束。

<div class='goodcode'></div>

```python
Yes:
  _T = TypeVar("_T")
  _P = ParamSpec("_P")
  AddableType = TypeVar("AddableType", int, float, str)
  AnyFunction = TypeVar("AnyFunction", bound=Callable)
```

<div class='badcode'></div>

```python
No:
  T = TypeVar("T")
  P = ParamSpec("P")
  _T = TypeVar("_T", int, float, str)
  _F = TypeVar("_F", bound=Callable)
```

<a id="s3.19.11-string-types"></a>
<a id="s3.19.11-strings"></a>
<a id="31911-string-types"></a>

<a id="typing-strings"></a>

#### 3.19.11 字串型別

> 新程式碼不要使用 `typing.Text`，它僅供 Python 2／3 相容使用。

字串／文字資料使用 `str`。處理二進位資料的程式碼使用 `bytes`。

<div class='goodcode'></div>

```python
def deals_with_text_data(x: str) -> str:
  ...
def deals_with_binary_data(x: bytes) -> bytes:
  ...
```

若函式的所有字串型別永遠相同，例如上述程式碼中的回傳值與引數型別相同，應使用 [AnyStr](#typing-type-var)。

<a id="s3.19.12-imports-for-typing"></a>
<a id="s3.19.12-imports"></a>
<a id="31912-imports-for-typing"></a>

<a id="typing-imports"></a>

#### 3.19.12 型別標註所需的匯入

對 `typing` 或 `collections.abc` 模組中用來支援靜態分析及型別檢查的符號，包含型別、函式與常數，一律直接匯入符號本身。這能讓常見註記更精簡，也符合普遍的型別標註實務。明確允許在同一行匯入這兩個模組中的多個特定符號。例如：

<div class='goodcode'></div>

```python
from collections.abc import Mapping, Sequence
from typing import Any, Generic, cast, TYPE_CHECKING
```

這種匯入方式會將名稱加入區域命名空間，因此應將 `typing` 或 `collections.abc` 的名稱視為類似關鍵字，不應在自己的 Python 程式碼中重新定義，無論有無型別註記。若型別與模組中既有名稱衝突，以 `import x as y` 匯入。

<div class='goodcode'></div>

```python
from typing import Any as AnyType
```

標註函式簽章時，優先使用 `collections.abc.Sequence` 等抽象容器型別，而非 `list` 等具體型別。若必須使用具體型別，例如包含各自具型別元素的 `tuple`，應優先使用 `tuple` 等內建型別，而非 `typing` 模組中的參數化型別別名，例如 `typing.Tuple`。

<div class='badcode'></div>

```python
from typing import List, Tuple

def transform_coordinates(original: List[Tuple[float, float]]) ->
    List[Tuple[float, float]]:
  ...
```

<div class='goodcode'></div>

```python
from collections.abc import Sequence

def transform_coordinates(original: Sequence[tuple[float, float]]) ->
    Sequence[tuple[float, float]]:
  ...
```

<a id="s3.19.13-conditional-imports"></a>
<a id="31913-conditional-imports"></a>

<a id="typing-conditional-imports"></a>

#### 3.19.13 條件式匯入

只有在特殊情況下，必須避免於執行階段載入型別檢查所需的額外匯入時，才使用條件式匯入。不鼓勵這種模式；應優先考慮重構程式碼以允許頂層匯入等替代方案。

僅供型別註記使用的匯入，可以放在 `if TYPE_CHECKING:` 區塊內。

-   條件式匯入的型別必須以字串參照，以相容於會實際求值註記運算式的 Python 3.6。
-   此處只能定義專供型別標註使用的實體，包含別名。否則會產生執行階段錯誤，因為執行時並未匯入模組。
-   區塊應緊接在所有一般匯入之後。
-   型別匯入清單內不應有空行。
-   依一般匯入清單的方式排序。

<div class='goodcode'></div>

```python
import typing
if typing.TYPE_CHECKING:
  import sketch
def f(x: "sketch.Sketch"): ...
```

<a id="s3.19.14-circular-dependencies"></a>
<a id="s3.19.14-circular-deps"></a>
<a id="31914-circular-dependencies"></a>

<a id="typing-circular-deps"></a>

#### 3.19.14 循環相依

型別標註造成的循環相依，是程式碼異味，適合重構。技術上雖可保留循環相依，但許多建置系統不允許，因為兩個模組會互相依賴。

以 `Any` 取代會造成循環相依的模組匯入。設定具意義名稱的[別名](#typing-aliases)，再使用該模組真正的型別名稱；`Any` 的任何屬性仍是 `Any`。別名定義與最後一個匯入之間應空一行。

<div class='goodcode'></div>

```python
from typing import Any

some_mod = Any  # some_mod.py 會匯入目前這個模組。
...

def my_method(self, var: "some_mod.SomeType") -> None:
  ...
```

<a id="typing-generics"></a>
<a id="s3.19.15-generics"></a>
<a id="31915-generics"></a>

<a id="generics"></a>

#### 3.19.15 泛型

標註[泛型](https://docs.python.org/3/library/typing.html#generics)時，優先在參數串列中指定型別參數；否則泛型參數會被視為 [`Any`](https://docs.python.org/3/library/typing.html#the-any-type)。

<div class='goodcode'></div>

```python
# 正確：
def get_names(employee_ids: Sequence[int]) -> Mapping[int, str]:
  ...
```

<div class='badcode'></div>

```python
# 錯誤：
# 這會被解讀為 get_names(employee_ids: Sequence[Any]) -> Mapping[Any, Any]
def get_names(employee_ids: Sequence) -> Mapping:
  ...
```

若泛型最適合的型別參數是 `Any`，應明確寫出。但請記得，許多情況下 [`TypeVar`](#typing-type-var) 可能更適合：

<div class='badcode'></div>

```python
# 錯誤：
def get_names(employee_ids: Sequence[Any]) -> Mapping[Any, str]:
  """回傳指定員工 ID 對應至員工姓名的映射。"""
```

<div class='goodcode'></div>

```python
# 正確：
_T = TypeVar('_T')
def get_names(employee_ids: Sequence[_T]) -> Mapping[_T, str]:
  """回傳指定員工 ID 對應至員工姓名的映射。"""
```

<a id="4-parting-words"></a>

<a id="consistency"></a>

## 4 結語

*保持一致*。

修改程式碼時，先花幾分鐘觀察周圍程式碼，了解其風格。如果索引變數名稱以 `_idx` 結尾，你也應如此。如果註解周圍以井字號畫小框，你也應採相同方式。

風格指南的目的，是建立共通的程式碼表達方式，讓人專注於你說的內容，而非表達形式。我們在此提出整體風格規則，讓大家熟悉共通語彙，但局部風格也很重要。如果新加入檔案的程式碼與周圍既有內容差異很大，就會打亂讀者的閱讀節奏。

然而，一致性也有界限。它更適用於局部，以及整體風格未規定的選擇。一般而言，不應以一致性為由，持續使用舊風格，而不考慮新風格的好處，或程式碼隨時間逐漸採用新風格的趨勢。
