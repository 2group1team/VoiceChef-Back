import logging
from contextlib import contextmanager
from typing import Generator, TypeVar, Callable, Any
from functools import wraps
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from fastapi import HTTPException, status

# Настройка логирования
logger = logging.getLogger(__name__)

T = TypeVar('T')


class TransactionError(Exception):
    """Базовое исключение для ошибок транзакций"""
    pass


class UniqueViolationError(TransactionError):
    """Исключение для нарушения уникальности"""
    pass


class ForeignKeyViolationError(TransactionError):
    """Исключение для нарушения внешнего ключа"""
    pass


@contextmanager
def transaction(db: Session, *, error_msg: str = None) -> Generator:
    transaction = db.begin_nested()
    try:
        yield
        transaction.commit()
        db.commit()
    except IntegrityError as e:
        transaction.rollback()
        db.rollback()
        logger.error(f"Integrity error in transaction: {str(e)}")

        if "unique violation" in str(e).lower():
            raise UniqueViolationError("Record already exists")
        elif "foreign key violation" in str(e).lower():
            raise ForeignKeyViolationError("Referenced record does not exist")
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg or "Database integrity error"
            )
    except SQLAlchemyError as e:
        transaction.rollback()
        db.rollback()
        logger.error(f"Database error in transaction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg or f"Database transaction failed: {str(e)}"
        )
    except Exception as e:
        transaction.rollback()
        db.rollback()
        logger.error(f"Unexpected error in transaction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg or "Internal server error during transaction"
        )


def transactional(error_msg: str = None) -> Callable:

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            db = next((arg for arg in args if isinstance(arg, Session)),
                      kwargs.get('db'))

            if not db:
                raise ValueError("Database session not found in arguments")

            with transaction(db, error_msg=error_msg):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def retry_transaction(
        max_retries: int = 3,
        retry_on: tuple = (SQLAlchemyError,),
        error_msg: str = None
) -> Callable:

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_error = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_error = e
                    logger.warning(
                        f"Transaction attempt {attempt + 1} of {max_retries} failed: {str(e)}"
                    )
                    if attempt == max_retries - 1:
                        break
                    continue
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=error_msg or str(e)
                    )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg or f"Transaction failed after {max_retries} attempts: {str(last_error)}"
            )

        return wrapper

    return decorator
