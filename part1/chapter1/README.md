# Chapter 1 도메인 모델링
- 도메인 모델링(domain modeling)
- 엔티티(entity)
- 값 객체(value object)
- 도메인 서비스(domain service)

## 1.1 도메인 모델이란?
비즈니스 로직 계층(business logic layer)을 도메인 모델(domain model)로 부른다.

- `도메인(domain)`: 비즈니스에서 해결하고자 하는 문제
- `모델(model)`: 유용한 특성을 포함하는 프로세스나 현상의 지도

도메인 모델은 비즈니스를 수행하는 사람이 자신의 비즈니스에 대해 마음속에 가지고 있는 지도와 같다. 이 지도는 인간이 복잡한 프로세스에 대해 생각하는 방식이다.

> 도메인 주도 설계(domain-driven design; DDD)에 따르면 소프트웨어에서 가장 중요한 요소는 문제에 대해 유용한 모델을 제공하는 것이다.

## 1.2 도메인 언어 탐구
도메인 언어를 이해하기 위해 비즈니스 전문가들과 모데인 모델에 사용할 용어와 규칙을 정해야 한다. 이때 가능한 각 규칙을 잘 보여주는 구체적인 예제를 요청한다.  
규칙은 비즈니스 전문용어(`유비쿼터스 언어(ubiquitous language)`)로 표현해야 한다. 도메인 모델은 개체에 식별자를 부여해 대상을 쉽게 공유할 수 있도록 한다.

## 1.3 도메인 모델 단위 테스트
단위 테스트의 이름은 시스템에서 사용자가 원하는 동작을 표현하도록 작성한다. 단위 테스트 클래스와 변수 이름은 비즈니스 전문용어에서 가져온다.

> typing.NewType으로 원시 타입을 감싸 타입 힌트를 더욱 명시적으로 사용할 수 있지만 과하므로 사용하지 않도록 한다.

### 1.3.1 값 객체로 사용하기 적합한 데이터 클래스
데이터는 있지만 유일한 식별자가 없는 비즈니스 개념을 표현하기 위해 `값 객체`를 사용한다.

- 값 객체(value object): 내장 데이터에 따라 유일하게 식별될 수 있는 도메인 객체; 보통 불변 객체(immutable object)

불변 객체를 표현하기 위해 `데이터 클래스(dataclass)` 또는 `네임드튜플(namedtuple)`을 사용할 수 있다. 이 표현의 장점은 값 동등성(value equality)을 부여할 수 있다는 것이다.

```python
from dataclasses import dataclass
from typing import NamedTuple
from collections import namedtuple

@dataclass(frozen=True)
class Name:
    first_name: str
    value: int

class Money(NamedTuple):
    currency: str
    value: int

Line = namedtuple('Line', ['sku', 'qty'])

def test_equality():
    assert Money('gbp', 10) == Money('gbp', 10)
    assert Name('Harry', 'Pericival') != Name('Bob', 'Gregory')
    assert Line('RED-CHAIR', 5) == Line('RED-CHAIR', 5)
```

### 1.3.2 값 객체와 엔티티
값과 달리 정체성 동등성(identity equality)이 있는 객체를 `엔티티`라고 한다.

- 엔티티(entity): 오랫동안 유지되는 정체성이 존재하는 도메인 객체

동등성 연산자를 구현함으로써 엔티티의 정체성 관련 동작을 명시적으로 작성할 수 있다.

```python
class Batch:
    ...

    def __eq__(self, other):
        if not isinstance(other, Batch):
            return False
        return other.reference == self.reference

    def __hash__(self):
        return hash(self.reference)
```
파이썬의 `__eq__` 마법 메서드(magic method)를 사용해 이 클래스가 == 연산자를 작동하는 방식을 정의한다. `__hash__`는 객체를 집합에 추가하거나 딕셔너리의 키로 사용할 때 동작을 제어하기 위해 사용한다.
> \_\_eq__를 변경하지 않았다면 \_\_hash__를 변경해서는 안 된다.

값 객체는 모든 값 속성을 사용해 해시를 정의하고 객체를 반드시 불변 객체로 만든다. 데이터 클래스의 `@frozen=True`를 지정하면 된다.  
엔티티는 해시를 None으로 정의하여 객체에 대한 해시를 계산할 수 없고 집합 등에서 사용하지 못하도록 할 수 있다. 엔티티를 집합에 넣거나 딕셔너리의 키로 사용해야 한다면 시간과 무관하게 엔티티의 정체성을 식별해주는 `읽기 전용 속성`을 사용해 해시를 정의해야 한다(예: .reference).

## 1.4 모든 것을 객체로 만들 필요는 없다: 도메인 서비스 함수
`도메인 서비스(domain service)`는 엔티티나 값 객체로 표현할 수 없는 비즈니스 개념이나 프로세스이다. 파이썬이 다중 패러다임 언어임을 이용하여 도메인 서비스를 함수로 구현할 수 있다.

```python
def allocate(line: OrderLine, batches: List[Batch]) -> str:
    batch = next(
        b for b in sorted(batches) if b.can_allocate(line)
    )
    batch.allocate(line)
    return batch.reference
```

### 1.4.1 파이썬 마법 메서드 사용 시 모델과 파이썬 숙어 함께 사용 가능
sorted()를 사용하기 위해 도메인 모델에 \_\_gt__를 구현해야 한다.
```python
class Batch:
    ...

    def __gt__(self, other):
        if self.eta == None:
            return False
        if other.eta == None:
            return True
        return self.eta > other.eta
```

### 1.4.2 예외를 사용해 도메인 개념 표현 가능
`도메인 예외(domain exception)`을 이용해 품절로 주문을 할당할 수 없는 경우와 같은 예외를 표현할 수 있다.

```python
class OutOfStock(Exception):
    pass
```

## 도메인 모델링 정리
- **도메인 모델링**  
도메인 모델링은 비즈니스와 가장 가까운 부분으로 변화가 생길 가능성이 가장 높고, 비즈니스에게 가장 큰 가지를 제공하는 부분이다.
- **엔티티와 값 객체 구분**  
값 객체는 내부 속성들에 정의되며 불변 타입을 사용해 구현한다. 값 객체의 속성을 변경하면 새로운 값 객체가 된다. 엔티티는 시간에 따라 변하는 속성이 포함될 수 있고, 이 속성이 바뀌더라도 여전히 똑같은 엔티티로 남는다.
- **모든 것을 객체로 만들 필요가 없다.**  
파이썬은 다중 패러다임 언어다. 따라서 동사(verb)에 해당하는 부분을 표현하려면 함수를 사용하는 것이 좋다.