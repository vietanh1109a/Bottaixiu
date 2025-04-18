import os
import random
import time
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram.error import TimedOut, RetryAfter, NetworkError
from collections import deque

# Lưu trữ số dư của người dùng
user_balances = {}
# Danh sách admin
admin_ids = [5786382877]  # Thay bằng ID Telegram của bạn

# Lưu trữ lịch sử kết quả tài xỉu (tối đa 20 kết quả gần nhất)
history_results = deque(maxlen=20)  # Sử dụng deque để giới hạn số lượng phần tử

# Biểu tượng và văn bản được làm đẹp
ICONS = {
    "money": "💰",
    "wallet": "👛",
    "win": "🎉",
    "lose": "😢",
    "dice": "🎲",
    "loading": "⏳",
    "deposit": "💵",
    "admin": "👑",
    "error": "❌",
    "success": "✅",
    "warning": "⚠️",
    "info": "ℹ️",
    "tai": "🔴",
    "xiu": "🔵",
    "history": "📜",
    "processing": "🎯",
    "balance": "💎",
    "trophy": "🏆",
    "fire": "🔥",
    "cool": "❄️",
    "rocket": "🚀",
    "star": "⭐",
}

# Hàm gửi tin nhắn an toàn với xử lý lỗi
async def safe_send_message(update, context, text):
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            return await update.message.reply_text(text)
        except (TimedOut, NetworkError, RetryAfter) as e:
            retry_count += 1
            if isinstance(e, RetryAfter):
                # Nếu bị giới hạn tốc độ, đợi theo yêu cầu + thêm 1 giây
                await asyncio.sleep(e.retry_after + 1)
            else:
                # Đối với các lỗi khác, đợi thời gian tăng dần
                await asyncio.sleep(1 * retry_count)
            
            if retry_count >= max_retries:
                # Nếu thử lại quá nhiều lần, ghi log và bỏ qua
                print(f"Không thể gửi tin nhắn sau {max_retries} lần thử: {e}")
                return None

# Hàm gửi xúc xắc an toàn
async def safe_send_dice(update, context):
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            return await update.message.reply_dice(emoji='🎲')
        except (TimedOut, NetworkError, RetryAfter) as e:
            retry_count += 1
            if isinstance(e, RetryAfter):
                await asyncio.sleep(e.retry_after + 1)
            else:
                await asyncio.sleep(1 * retry_count)
            
            if retry_count >= max_retries:
                print(f"Không thể gửi xúc xắc sau {max_retries} lần thử: {e}")
                return None

# Hàm xóa tin nhắn an toàn
async def safe_delete_message(context, chat_id, message_id):
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            return await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except (TimedOut, NetworkError, RetryAfter) as e:
            retry_count += 1
            if isinstance(e, RetryAfter):
                await asyncio.sleep(e.retry_after + 1)
            else:
                await asyncio.sleep(1 * retry_count)
            
            if retry_count >= max_retries:
                print(f"Không thể xóa tin nhắn sau {max_retries} lần thử: {e}")
                return None

# Hàm kiểm tra số dư
async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    balance = user_balances.get(user_id, 0)
    await safe_send_message(update, context, f"{ICONS['wallet']} Số dư của bạn: {ICONS['money']} {balance:,} đồng")

# Hàm nạp tiền (chỉ admin)
async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    # In ra ID người dùng để dễ thêm admin
    await safe_send_message(update, context, f"{ICONS['info']} User ID của bạn là: {user_id}")
    
    # Kiểm tra xem người dùng có phải là admin không
    if user_id not in admin_ids:
        await safe_send_message(update, context, f"{ICONS['error']} Bạn không có quyền sử dụng lệnh này!")
        return
    
    # Kiểm tra đúng định dạng lệnh
    if len(context.args) != 2:
        await safe_send_message(update, context, f"{ICONS['warning']} Sử dụng: /naptien [user_id] [số tiền]")
        return
    
    try:
        target_user_id = int(context.args[0])
        amount = int(context.args[1])
        
        if amount <= 0:
            await safe_send_message(update, context, f"{ICONS['warning']} Số tiền phải lớn hơn 0!")
            return
        
        # Cập nhật số dư
        if target_user_id not in user_balances:
            user_balances[target_user_id] = amount
        else:
            user_balances[target_user_id] += amount
        
        await safe_send_message(update, context, 
            f"{ICONS['success']} Đã nạp {ICONS['deposit']} {amount:,} đồng cho người dùng {target_user_id}.\n"
            f"{ICONS['wallet']} Số dư hiện tại: {ICONS['money']} {user_balances[target_user_id]:,} đồng")
    
    except ValueError:
        await safe_send_message(update, context, f"{ICONS['error']} ID người dùng và số tiền phải là số!")

# Hàm nạp tiền cho bản thân
async def self_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    # Kiểm tra admin
    if user_id not in admin_ids:
        await safe_send_message(update, context, f"{ICONS['error']} Bạn không có quyền sử dụng lệnh này!")
        return
    
    # Kiểm tra định dạng
    if len(context.args) != 1:
        await safe_send_message(update, context, f"{ICONS['warning']} Sử dụng: /napcho [số tiền]")
        return
    
    try:
        amount = int(context.args[0])
        
        if amount <= 0:
            await safe_send_message(update, context, f"{ICONS['warning']} Số tiền phải lớn hơn 0!")
            return
        
        # Cập nhật số dư
        if user_id not in user_balances:
            user_balances[user_id] = amount
        else:
            user_balances[user_id] += amount
        
        await safe_send_message(update, context, 
            f"{ICONS['success']} Đã nạp {ICONS['deposit']} {amount:,} đồng cho bạn.\n"
            f"{ICONS['wallet']} Số dư hiện tại: {ICONS['money']} {user_balances[user_id]:,} đồng")
    
    except ValueError:
        await safe_send_message(update, context, f"{ICONS['error']} Số tiền phải là số!")

# Tạo chuỗi lịch sử kết quả
def get_history_string():
    if not history_results:
        return f"{ICONS['warning']} Chưa có lịch sử"
    
    # Tạo chuỗi emoji từ lịch sử kết quả
    history_icons = ""
    for result in history_results:
        history_icons += ICONS[result]
    
    return history_icons

# Hàm xem lịch sử
async def view_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    history_icons = get_history_string()
    await safe_send_message(update, context, f"{ICONS['history']} Cầu hiện tại:\n{history_icons}")

# Hàm chơi tài xỉu
async def taixiu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    # Kiểm tra đúng định dạng lệnh
    if len(context.args) != 2:
        await safe_send_message(update, context, f"{ICONS['warning']} Sử dụng: /taixiu [tai/xiu] [số tiền]")
        return
    
    choice = context.args[0].lower()
    if choice not in ["tai", "xiu"]:
        await safe_send_message(update, context, f"{ICONS['error']} Lựa chọn phải là 'tai' hoặc 'xiu'!")
        return
    
    try:
        bet_amount = int(context.args[1])
        
        # Kiểm tra số tiền hợp lệ
        if bet_amount <= 0:
            await safe_send_message(update, context, f"{ICONS['warning']} Số tiền cược phải lớn hơn 0!")
            return
        
        # Kiểm tra số dư
        balance = user_balances.get(user_id, 0)
        if balance < bet_amount:
            await safe_send_message(update, context, 
                f"{ICONS['error']} Mày hết tiền r ku! Mày có {ICONS['money']} {balance:,} đồng; "
                f"ib @vietlegendc để nạp tiền đê!!! {ICONS['rocket']}")
            return
        
        # Gửi tin nhắn đang xử lý
        processing_msg = await safe_send_message(update, context, 
            f"{ICONS['processing']} Đang tung xúc xắc... {ICONS['loading']}")
        if processing_msg is None:
            await safe_send_message(update, context, f"{ICONS['error']} Có lỗi xảy ra, vui lòng thử lại sau.")
            return
        
        # Hiển thị lựa chọn của người chơi
        choice_icon = ICONS["tai"] if choice == "tai" else ICONS["xiu"]
        await safe_send_message(update, context, f"Bạn đã chọn: {choice_icon} {choice.upper()}")
        
        # Tung xúc xắc
        dice1 = await safe_send_dice(update, context)
        if dice1 is None:
            await safe_send_message(update, context, f"{ICONS['error']} Có lỗi xảy ra khi tung xúc xắc, vui lòng thử lại sau.")
            return
        await asyncio.sleep(1)  # Đợi 1 giây
        
        dice2 = await safe_send_dice(update, context)
        if dice2 is None:
            await safe_send_message(update, context, f"{ICONS['error']} Có lỗi xảy ra khi tung xúc xắc, vui lòng thử lại sau.")
            return
        await asyncio.sleep(1)  # Đợi 1 giây
        
        dice3 = await safe_send_dice(update, context)
        if dice3 is None:
            await safe_send_message(update, context, f"{ICONS['error']} Có lỗi xảy ra khi tung xúc xắc, vui lòng thử lại sau.")
            return
        
        # Đợi để animation hoàn thành
        await asyncio.sleep(2)  # Giảm thời gian chờ animation xuống 2 giây để tránh timeout
        
        # Lấy kết quả
        dice_value1 = dice1.dice.value
        dice_value2 = dice2.dice.value
        dice_value3 = dice3.dice.value
        
        total = dice_value1 + dice_value2 + dice_value3
        result = "tai" if total >= 10 else "xiu"
        result_icon = ICONS["tai"] if result == "tai" else ICONS["xiu"]
        
        # Thêm kết quả vào lịch sử
        history_results.append(result)
        
        # Lấy chuỗi lịch sử
        history_icons = get_history_string()
        
        # Xóa tin nhắn đang xử lý (không quan trọng nếu không thành công)
        await safe_delete_message(context, update.effective_chat.id, processing_msg.message_id)
        
        # Hiệu ứng thêm tùy thuộc vào số điểm
        dice_effect = ""
        if total >= 16:
            dice_effect = f"{ICONS['fire']} SUPER HIGH! {ICONS['fire']}"
        elif total <= 4:
            dice_effect = f"{ICONS['cool']} SUPER LOW! {ICONS['cool']}"
        
        # Kiểm tra kết quả
        if choice == result:
            # Thắng
            winnings = int(bet_amount * 1.9)
            user_balances[user_id] = balance + winnings - bet_amount
            
            # Thông báo đặc biệt cho thắng lớn
            win_message = f"{ICONS['win']} Chúc mừng! Bạn đã thắng {ICONS['money']} {winnings:,} đồng!"
            if winnings >= 100000:
                win_message = f"{ICONS['trophy']} {ICONS['win']} JACKPOT! Bạn đã thắng {ICONS['money']} {winnings:,} đồng! {ICONS['win']} {ICONS['trophy']}"
            
            await safe_send_message(update, context,
                f"{ICONS['dice']} Kết quả: {dice_value1} + {dice_value2} + {dice_value3} = {total} {result_icon} ({result.upper()}) {dice_effect}\n"
                f"{win_message}\n"
                f"{ICONS['wallet']} Số dư hiện tại: {ICONS['money']} {user_balances[user_id]:,} đồng\n"
                f"{ICONS['history']} Cầu hiện tại: {history_icons}"
            )
        else:
            # Thua
            user_balances[user_id] = balance - bet_amount
            await safe_send_message(update, context,
                f"{ICONS['dice']} Kết quả: {dice_value1} + {dice_value2} + {dice_value3} = {total} {result_icon} ({result.upper()}) {dice_effect}\n"
                f"{ICONS['lose']} Rất tiếc! Bạn đã thua {ICONS['money']} {bet_amount:,} đồng.\n"
                f"{ICONS['wallet']} Số dư hiện tại: {ICONS['money']} {user_balances[user_id]:,} đồng\n"
                f"{ICONS['history']} Cầu hiện tại: {history_icons}"
            )
    
    except ValueError:
        await safe_send_message(update, context, f"{ICONS['error']} Số tiền phải là số!")
    except Exception as e:
        print(f"Lỗi không xác định trong hàm taixiu: {e}")
        await safe_send_message(update, context, f"{ICONS['error']} Có lỗi xảy ra, vui lòng thử lại sau.")

# Hàm xử lý lỗi
async def error_handler(update, context):
    print(f"Lỗi: {context.error}")
    if update:
        try:
            await update.message.reply_text(f"{ICONS['error']} Có lỗi xảy ra, vui lòng thử lại sau.")
        except:
            pass

def main() -> None:
    # Tạo ứng dụng với các cài đặt timeout qua ApplicationBuilder
    application = Application.builder()\
        .token("7588859368:AAGNI2p2vuT0HdjePw1_TKSpjjvYRa4Y0xc")\
        .get_updates_read_timeout(30)\
        .get_updates_write_timeout(30)\
        .get_updates_connect_timeout(30)\
        .get_updates_pool_timeout(30)\
        .build()

    # Thêm các handlers
    application.add_handler(CommandHandler("sodu", check_balance))
    application.add_handler(CommandHandler("naptien", deposit))
    application.add_handler(CommandHandler("napcho", self_deposit))
    application.add_handler(CommandHandler("taixiu", taixiu))
    application.add_handler(CommandHandler("cau", view_history))

    # Thêm error handler để xử lý lỗi
    application.add_error_handler(error_handler)

    # Chạy bot (không cần thêm timeout parameters vào run_polling)
    print(f"{ICONS['rocket']} Bot Tài Xỉu đã khởi động!")
    application.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()