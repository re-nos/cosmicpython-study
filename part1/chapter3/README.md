# Chapter 3 결합과 추상화
어떤 컴포넌트가 깨지는 게 두려워 다른 컴포넌트를 변경할 수 없는 경우에 두 컴포넌트가 서로 `결합`되어 있다고 한다.  
지역적인 결합은 `응집(cohesion)`이라고 하며 바람직한 경우이다. 그러나 전역적인 결합은 코드 변경 비용을 증가시킨다. 애플리케이션이 커짐에 따라 결합이 요소의 개수가 늘어나는 비율보다 훨씬 더 빨리 증가하여 시스템을 실질적으로 변경할 수 없게 된다.  

이때 추상화를 통해 세부 사항을 감추면 시스템 내 결합 정도를 줄일 수 있다.

## 3.1 추상적인 상태는 테스트를 더 쉽게 해준다
예를 들어 두 파일 디레터리를 동기화하는 코드를 작성한다고 하자. 두 파일 디렉토리는 각각 **원본(source)** 과 **사본(destination)** 이며 요구사항은 다음과 같다.  

1. 원본에 파일이 있지만 사본에 없으면 파일을 원본에서 사본으로 복사한다.
2. 원본에 파일이 있지만 사본에 있는 (내용이 같은) 파일과 이름이 다르면 사본의 파일 이름을 원본 파일 이름과 같게 변경한다.
3. 사본에 파일이 있지만 원본에는 없다면 사본의 파일을 삭제한다.

처음부터 문제를 해결하는 경우 보통 간단한 구현을 작성한 다음 리팩터링한다. 문제의 가장 작은 부분부터 해결하는 방법으로 시작하여 더 풍부하고, 더 좋은 해법의 설계를 만들어가는 것을 반복한다.  

처음 해법은 다음과 같다.

```python
import os
import shutil
import hashlib
from pathlib import Path

def sync(source, dest):
    source_hashes = {}

    for folder, _, files in os.walk(source):
        for fn in files:
            source_hashes[hash_file(Path(folder) / fn)] = fn

    seen = set()

    for folder, _, files in os.walk(dest):
        for fn in files:
            dest_path = Path(folder) / fn
            dest_hash = hash_file(dest_path)
            seen.add(dest_hash)

            if dest_hash not in source_hashes:
                dest_path.remove()

            elif dest_hash in source_hashes and fn != source_hashes[dest_hash]:
                shutil.move(dest_path, Path(folder) / source_hashes[dest_hash])

    for src_hash, fn in source_hashes.items():
        if src_hash not in seen:
            shutil.copy(Path(source) / fn, Path(dest) / fn)
```

위 코드에는 여러 문제점이 있다.

- '두 디렉터리의 차이 알아내기' 도메인 로직이 I/O 코드와 긴밀히 결합됨
    - pathlib, shutil, hashlib 모듈을 모두 호출해야 함
- 테스트가 충분하지 않음
    - 테스트 커버리지를 달성하고 버그를 찾기 위해 많은 테스트가 필요함
    - 테스트를 위해 많은 준비 과정이 필요하여 작성이 번거로움
- 확장성이 좋지 않음
    - 어떤 작업을 수행해야 할지 표시해주는 --dry-run 플래그를 구현한다면?
    - 원격 서버나 클라우드 저장 장치와 동기화하려면?

## 3.2 올바른 추상화 선택
테스트하기 쉽도록 코드를 작성하기 위해 다음을 고려한다.  

먼저 파일 시스템의 어떤 기능을 코드에서 사용할지 생각하고, 코드의 책임을 세 가지로 분리한다.
1. `os.walk`를 사용해 파일 시스템 정보를 얻고, 그로부터 파일 내용의 해시를 결정할 수 있다. 이 동작은 원본과 사본 디렉터리에서 같다.
2. 파일이 새 파일인지, 이름이 변경된 파일인지, 중복된 파일인지 결정한다.
3. 원본과 사본을 일치시키기 위해 파일을 복사하거나 옮기거나 삭제한다.

이 세 가지 책임에 대해 더 `단순화한 추상화(simplifying abstraction)`를 찾는다. 추상화를 하면 세부 사항을 감추고 로직에만 집중할 수 있다.

- 파일 경로와 해시를 엮는 사전 생성 시 원본 폴더뿐 아니라 사본 폴더에 대한 사전도 생성
- **무엇(what)** 을 원하는가와 원하는 바를 **어떻게(how)** 달성할지를 분리
    - 프로그램이 다음과 비슷한 명령 목록을 출력하도록 구현
    ```python
    ('COPY', 'sourcepath', 'destpath'),
    ('MOVE', 'old', 'new')
    ```
    - 이로 인해 파일 시스템을 표현하는 두 사전을 입력받는 테스트 작성 가능
    - 실제 파일 시스템이 아닌 파일 시스템의 추상화에 함수를 실행하였을 때의 추상화된 동작 확인 가능

## 3.3 선택한 추상화 구현
실제로 새로운 테스트를 어떻게 작성해야 할까? 목표는 다음과 같다.
- 시스템에서 트릭이 적용된 부분을 분리해서 격리
- 실제 파일 시스템 없이도 테스트 가능하도록 함

이를 위해 먼저 코드에서 로직과 상태가 있는 부분을 분리한다. 최상위 코드는 로직 없이 1) 입력을 수집하고 2) 로직을 호출한 후 3) 출력을 적용하는 명령형 코드를 나열한다.

```python
def sync(source, dest):
    source_hashes = read_paths_and_hashes(source)
    dest_hashes = read_paths_and_hashes(dest)
    
    actions = determine_actions(source_hashes, dest_hashes, source, dest)
    
    for action, *paths in actions:
        if action == 'copy':
            shutil.copyfile(*paths)
        if action == 'move':
            shutil.move(*paths)
        if action == 'delete':
            os.remove(paths[0])
```

파일 경로와 파일 해시로 이루어진 사전을 만드는 코드를 쉽게 작성할 수 있다.

```python
def read_paths_and_hashes(root):
    hashes = {}
    for folder, _, files in os.walk(root):
        for fn in files:
            hashes[hash_file(Path(folder) / fn)] = fn
    return hashes
```

`determine_actions()` 함수는 비즈니스 로직의 핵심이다. 간단한 데이터 구조를 입력으로 받고 간단한 데이터를 출력으로 돌려준다.

```python
def determine_actions(src_hashes, dst_hashes, src_folder, dst_folder):
    for sha, filename in src_hashes.items():
        if sha not in dst_hashes:
            sourcepath = Path(src_folder) / filename
            destpath = Path(dst_folder) / filename
            yield 'copy', sourcepath, destpath
        
        elif dst_hashes[sha] != filename:
            olddestpath = Path(dst_folder) / dst_hashes[sha]
            newdestpath = Path(dst_folder) / filename
            yield 'move', olddestpath, newdestpath
            
    for sha, filename in dst_hashes.items():
        if sha not in src_hashes:
            yield 'delete', dst_folder / filename
```

프로그램의 로직과 저수준 I/O 세부 사항 사이의 얽힘을 풀었기 때문에 쉽게 코드의 핵심 로직인 `determine_actions()` 함수를 테스트할 수 있다.

```python
def test_when_a_file_exists_in_the_source_but_not_the_destination():
    src_hashes = {'hash1': 'fn1'}
    dst_hashes = {}
    
    actions = determine_actions(src_hashes, dst_hashes, Path('/src'), Path('/dst'))
    
    assert list(actions) == [('copy', Path('/src/fn1'), Path('/dst/fn1'))]
```

전체 통합/인수 테스트를 유지할 수도 있지만, `sync()`함수를 수정해서 단위 테스트도 가능하다. 엔드투엔드 테스트도 가능하다. 이런 접근 방법을 `에지투에지(edge-to-edge)` 테스트라고 한다.

### 3.3.1 의존성 주입과 가짜를 사용해 에지투에지 테스트
새로운 시스템을 작성하고 어느 시점이 되면 큰 덩어리를 한번에 테스트하려고 할 것이다. 이때 엔드투엔드 테스트보다 가짜 I/O를 사용하는 일종의 에지투에지 테스트를 작성할 수 있다.

이러한 접근 장단점은 다음과 같다.
- 장점: 테스트가 프로덕션 코드에 사용되는 함수와 완전히 같은 함수에 작용함 
- 단점: 상태가 있는 요소들을 명시적으로 표현해 전달하면서 작업을 수행해야 함

### 3.3.2 패치를 사용하지 않는 이유
`mock.patch`보다 `테스트 더블`을 사용하는 이유는 다음과 같다.

- 사용 중인 의존성을 다른 코드로 패치하면 코드를 단위 테스트할 수는 있지만 설계를 개선하는 데는 아무 역할도 하지 않는다.
- 목을 사용한 테스트는 코드베이스의 구현 세부 사항에 더 밀접히 결합된다. 목이 여러 요소 사이의 상호작용을 검증하기 때문이다.
- 목을 과용하면 테스트 스위트가 복잡해져서 테스트 대상 코드의 동작을 알아내기가 어렵다.

> `목(mock)`은 대상이 어떻게 쓰이는지를 검증할 때 사용하고, `가짜 객체(fake object)`는 대치하려는 대상을 동작할 수 있게 구현한 존재이다.

## 3.4 마치며
비즈니스 로직과 I/O 사이의 인터페이스를 단순화하여 시스템을 더 쉽게 테스트하고 유지보수할 수 있도록 한다. 올바른 추상화를 찾기 위해 다음 몇 가지 질문을 던져보자.

- 지저분한 시스템의 상태를 표현할 수 있는 익숙한 파이썬 객체가 있는가? 그렇다면 이를 활용해 시스템 상태를 반환하는 단일 함수를 생각해보자.
- 시스템의 구성 요소 중 어떤 부분에 선을 그을 수 있는가? 이런 추상화 사이의 이음매를 어떻게 만들 수 있는가?
- 시스템의 여러 부분을 서로 다른 책임을 지니는 구성 요소로 나누는 합리적인 방법은 무엇일까? 명시적으로 표현해야 하는 암시적인 개념은 무엇인가?
- 어떤 의존 관계가 존재하는가? 핵심 비즈니스 로직은 무엇인가?
