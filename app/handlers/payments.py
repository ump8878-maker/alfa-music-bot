from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    PreCheckoutQuery,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.models import Payment, UserUnlock
from app.models.payment import Products, UnlockType

router = Router()


@router.callback_query(F.data.startswith("buy:"))
async def buy_product(callback: CallbackQuery, session: AsyncSession):
    """Покупка продукта через Telegram Stars"""
    product_id = callback.data.split(":")[1]
    
    products = {
        Products.UNLOCK_MATCHES["id"]: Products.UNLOCK_MATCHES,
        Products.WHO_CHOSE_ME["id"]: Products.WHO_CHOSE_ME,
        Products.FULL_INSIGHTS["id"]: Products.FULL_INSIGHTS,
        Products.PREMIUM_WEEK["id"]: Products.PREMIUM_WEEK,
    }
    
    product = products.get(product_id)
    if not product:
        await callback.answer("Продукт не найден", show_alert=True)
        return
    
    prices = [LabeledPrice(label=product["title"], amount=product["price"])]
    
    await callback.message.answer_invoice(
        title=product["title"],
        description=f"Разблокировка: {product['title']}",
        payload=f"{product_id}:{callback.from_user.id}",
        currency="XTR",
        prices=prices,
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, session: AsyncSession):
    """Подтверждение платежа"""
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message, session: AsyncSession):
    """Обработка успешного платежа"""
    payment_info = message.successful_payment
    payload_parts = payment_info.invoice_payload.split(":")
    product_id = payload_parts[0]
    user_id = int(payload_parts[1])
    
    payment = Payment(
        user_id=user_id,
        amount=payment_info.total_amount,
        currency=payment_info.currency,
        product=product_id,
        status="completed",
        telegram_payment_id=payment_info.telegram_payment_charge_id,
    )
    session.add(payment)
    
    unlock_mapping = {
        Products.UNLOCK_MATCHES["id"]: UnlockType.ALL_MATCHES,
        Products.WHO_CHOSE_ME["id"]: UnlockType.WHO_CHOSE_ME,
        Products.FULL_INSIGHTS["id"]: UnlockType.FULL_INSIGHTS,
        Products.PREMIUM_WEEK["id"]: UnlockType.PREMIUM_WEEK,
    }
    
    unlock_type = unlock_mapping.get(product_id)
    if unlock_type:
        expires_at = None
        if unlock_type == UnlockType.PREMIUM_WEEK:
            expires_at = datetime.utcnow() + timedelta(days=7)
        
        unlock = UserUnlock(
            user_id=user_id,
            unlock_type=unlock_type,
            expires_at=expires_at,
        )
        session.add(unlock)
    
    await session.commit()
    
    await message.answer(
        "✅ <b>Оплата прошла успешно!</b>\n\n"
        "Функция разблокирована. Приятного использования! 🎵",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "add_to_chat")
async def add_to_chat_prompt(callback: CallbackQuery):
    """Предложение добавить бота в чат"""
    bot_info = await callback.bot.get_me()
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(
        text="➕ Добавить в чат",
        url=f"https://t.me/{bot_info.username}?startgroup=true"
    )
    
    await callback.message.answer(
        "👥 <b>Добавь бота в чат друзей!</b>\n\n"
        "Там ты сможешь:\n"
        "• Увидеть совпадения бесплатно\n"
        "• Запустить баттлы и угадайки\n"
        "• Узнать карту вкусов компании\n\n"
        "Нажми кнопку ниже 👇",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()
