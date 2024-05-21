# Chapter 2 저장소 패턴
- `저장소 패턴(repository pattern)`: 데이터 저장소를 더 간단히 추상화한 것  

저장소 패턴을 사용하여 모델 계층과 데이터 계층을 분리할 수 있다. 또한 데이터베이스의 복잡성을 감춰서 시스템을 테스트하기 더 좋게 만든다.

## 2.1 도메인 모델 영속화
애자일 방식으로 작업할 때 가능한 한 빨리 최소 기능 제품(minimum viable product; MVP)을 만드는 것이 우선이다.  
여기서는 웹 API가 MVP이다. 실전에서는 엔드투엔드 테스트로 바로 들어가서 웹 프레임워크에 기능을 넣고, 외부로부터 내부 방향으로 테스트를 시작한다.  
어떤 방식이든 영속적인 저장소가 필요하다.

## 2.2 의사코드: 무엇이 필요할까?
처음 API 엔드포인트(endpoint)를 만들 때 다음과 비슷한 코드를 작성한다.

```python
@flask.route.gubbins
def allocate_endpoint():
    line = OrderLine(request.params, ...)
    batch = ...
    allocate(line, batch)
    return 201
```

위 코드를 작성하기 위해 다음 방법이 필요하다.
- 배치 정보를 데이터베이스에서 가져와 도메인 모델 객체를 초기화하는 방법
- 도메인 객체 모델에 있는 정보를 데이터베이스에 저장하는 방법

## 2.3 데이터 접근에 DIP 적용하기
계층 아키텍처와 같이 계층을 분리하되 도메인 모델에는 어떤 의존성도 존재하지 않도록 한다. 의존성이 비즈니스 로직 즉, 도메인 모델로 들어오도록 만들어야 한다. 이런 방식을 `양파 아키텍처(onion architecture)`라고 한다.

```
표현 계층 --> 비즈니스 로직 <-- 데이터베이스 계층
```

높은 계층의 모듈(도메인)이 저수준의 모듈(하부구조)에 의존해서는 안 된다.

## 2.4 기억 되살리기: 우리가 사용하는 모델
할당은 `OrderLine`과 `Batch`를 연결하는 개념이다. 할당 정보를 Batch 객체의 컬렉션으로 저장한다. 이를 데이터베이스화 한다.

### 2.4.1 '일반적인' ORM 방식: ORM에 의존하는 모델
`객체 관계 매핑(object-relational mapping; ORM)`은 도메인 모델 객체와 데이터베이스를 연결하는 프레임워크이다.   
ORM이 제공하는 가장 중요한 기능은 `영속성 무지(persistence ignorance)`이다. 도메인 모델이 데이터를 어떻게 적재하고 영속화하는지에 대해 알 필요가 없도록 한다. 영속성 무지가 성립하면 특정 데이터베이스 기술에 도메인이 직접 의존하지 않도록 유지할 수 있다.  

그러나 전형적인 SQLAlchemy의 선언적(declarative) 문법을 사용하면 모델이 ORM에 의존하게 된다.

```python
Base = declarative_base()

class Order(Base):
    id = Column(Integer, primary_key=True)

class OrderLine(Base):
    id = Column(Integer, primary_key=True)
    sku = Column(String(255))
    qty = Column(Integer, nullable=False)
    order_id = Column(Integer, ForeignKey("order.id"))
    order = relationship(Order)

class Allocation(Base):
    ...
```

### 2.4.2 의존성 역전: 모델에 의존하는 ORM
모델에 의존하는 ORM을 작성하기 위해 스키마를 별도로 정의하고, 스키마와 도메인 모델을 상호 변환하는 명시적인 `매퍼(mapper)`를 정의한다. SQLAlchemy는 이를 `classical mapping` 또는 `Imperative mapping`라고 부른다.

```python
mapper_registry = registry()

order_lines = Table(
    "order_lines", mapper_registry.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("sku", String(255)),
    Column("qty", Integer, nullable=False),
)

...

def start_mappers():
    lines_mapper = mapper_registry.map_imperatively(model.OrderLine, order_lines)
```

명시적 매퍼를 정의하여 테이블이 도메인 모델을 의존하도록 한다. 즉, 도메인 모델이 ORM에 의존하지 않도록 한다.

## 2.5 저장소 패턴 소개
`저장소 패턴(repository pattern)`은 영속적 저장소를 추상화한 것이다. 저장소 패턴은 모든 데이터가 메모리상에 존재하는 것처럼 가정해 데이터 접근과 관련된 세부 사항을 감춘다.  
모든 객체가 메모리에 있더라도 이 객체들을 다시 찾을 수 있도록 어딘가에 보관해야 한다. 

### 2.5.1 추상화한 저장소
- `add()`: 새 원소를 저장소에 추가
- `get()`: 추가한 원소를 저장소에서 가져옴  

데이터에 접근할 때 위 두 메서드만 사용하도록 하면 도메인과 서비스 계층 사이의 결합을 끊을 수 있다. 추상 저장소는 `ABC`를 사용한다.

```python
import abc

class AbstractRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, batch: model.Batch):
        raise NotImplementedError
    
    @abc.abstractmethod
    def get(self, reference) -> model.Batch:
        raise NotImplementedError
```

> ABC는 무시하기가 쉬워 유지보수가 어려우므로 대안으로 덕 타이핑(duct typing)에 의존하거나 프로토콜(protocal)을 사용할 수 있다.

### 2.5.2 트레이드오프란 무엇인가?
트레이드오프는 새로운 것을 반영함으로 인해 얻는 이익과 비용을 의미한다. 보통 새로운 추상화 계층을 추가할 때 전체적인 복잡성이 최소한으로 줄어들기를 기대한다. 그러나 새 추상화는 지역적으로는 복잡성을 증가시키고, 지속적으로 유지보수해야 한다는 측면에서 비용이 증가한다.  
DDD와 의존성 역전을 택한 이상 저장소 패턴을 사용하는 것이 가장 쉽다. 저장소 패턴을 사용하면 사물을 저장하는 방법을 더 쉽게 바꿀 수 있고, 단위 테스트 시 가짜 저장소를 제공하기가 더 쉬워진다.

```
애플리케이션 계층 <--> 저장소 --> 데이터베이스 계층
                  L 도메인 모델 객체
```

테스트 작성 후 저장소를 작성한다.

```python
class SqlAlchemyRepository(AbstractRepository):
    def __init__(self, session):
        self.session = session
        
    def add(self, batch: model.Batch):
        self.session.add(batch)
        
    def get(self, reference) -> model.Batch:
        return self.session.query(model.Batch).filter_by(reference=reference).one()
    
    def list(self):
        return self.session.query(model.Batch).all()
```

## 2.6 테스트에 사용하는 가짜 저장소를 쉽게 만드는 방법
저장소 패턴을 사용하면 가짜 저장소를 쉽게 만들고 사용할 수 있다.

```python
class FakeRepository(AbstractRepository):
    def __init__(self, batches):
        self._batches = batches
        
    def add(self, batch):
        self._batches.add(batch)
        
    def get(self, reference):
        return next(b for b in self._batches if b.reference == reference)
    
    def list(self):
        return list(self._batches)


fake_repo = FakeRepository([batch1, batch2, batch3])
```

## 2.7 파이썬에서 포트는 무엇이고, 어댑터란 무엇인가
- 포트(port)
    - 애플리케이션과 추상화하려는 대상 사이의 인터페이스(interface)
    - 추상 기반 클래스
    - `AbstractRepository`
- 어댑터(adapter)
    - 인터페이스나 추상화가 뒤에 있는 구현(implementation)
    - `SqlAlchemyRepository`, `FakeRepository`

## 2.8 마치며
다음 표는 저장소 패턴과 영속성에 대해 무지한 모델의 장단점이다.

| 장점 | 단점 |
| --- | --- |
| 영속적 저장소와 도메인 모델 사이의 인터페이스를 간단하게 유지할 수 있다. | ORM이 어느 정도 (모델과 저장소의) 결합을 완화시켜준다. (ORM을 사용하면) 외래키를 변경하기는 어렵지만 필요할 때 MySQL과 Postgres를 서로 바꾸기 쉽다. |
| 모델과 인프라에 대한 사항을 완전히 분리했기 때문에 단위 테스트를 위한 가짜 저장소를 쉽게 만들 수 있고, 저장소 해법을 변경하기도 쉽다. | ORM 매핑을 수동으로 하려면 작업과 코드가 더 필요하다. |
| 영속성을 고려하기 전에 도메인 모델을 작성하면 비즈니스 문제에 집중하기 쉽다. 접근 방식을 극적으로 바꾸고 싶을 때 외래키나 마이그레이션 등을 고려하지 않고 모델에 이를 반영할 수 있다. | 간접 계층을 추가하면 유지보수 비용이 증가한다. |
| 객체를 테이블에 매핑하는 과정을 원하는 대로 제어할 수 있어서 데이터베이스 스키마를 단순화할 수 있다. | |

## 저장소 패턴 정리
- **ORM에 의존성 역전을 적용하자**  
ORM은 모델을 임포트해야 하며 모델이 ORM을 임포트해서는 안 된다.
- **저장소 패턴은 영속적 저장소에 대한 단순환 추상화다.**  
저장소를 사용하면 핵심 애플리케이션에는 영향을 미치지 않으면서 인프라를 이루는 세부 구조를 변경하거나 가짜 저장소를 쉽게 작성할 수 있다.