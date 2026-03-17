from discord import Embed, Message

from typing import Literal, Optional, overload

from db import get_db
from repository.borrow_repository import BorrowRepository
from repository.return_repository import ReturnRepository


async def request_timeout(message: Message, uid: int, is_borrow: bool):
    async with get_db() as conn:
        if is_borrow:
            await BorrowRepository.delete_by_uid(conn=conn, uid=uid)
        else:
            await ReturnRepository.delete_by_uid(conn=conn, uid=uid)

    if len(message.embeds) == 0:
        return
    embed = message.embeds[0]
    embed.color = 0x888888
    embed.title = "操作已過期"

    await message.edit(
        content="",
        embed=embed,
        view=None
    )

    print(f"Request timeout: uid={uid}, is_borrow={is_borrow}")


@overload
async def accept_or_reject_func(
    oper: Literal["accept", "reject"],
    uid: int,
    is_borrow: bool
) -> None: ...


@overload
async def accept_or_reject_func(
    oper: Literal["accept", "reject"],
    uid: int,
    is_borrow: bool,
    embed: None
) -> None: ...


@overload
async def accept_or_reject_func(
    oper: Literal["accept", "reject"],
    uid: int,
    is_borrow: bool,
    embed: Embed
) -> Embed: ...


async def accept_or_reject_func(
    oper: Literal["accept", "reject"],
    uid: int,
    is_borrow: bool,
    embed: Optional[Embed] = None
) -> Optional[Embed]:
    async with get_db() as conn:
        if oper == "accept":
            await (BorrowRepository if is_borrow else ReturnRepository).set_pending_by_uid(
                conn=conn,
                uid=uid,
                pending=False
            )
        elif oper == "reject":
            await (BorrowRepository if is_borrow else ReturnRepository).delete_by_uid(
                conn=conn,
                uid=uid
            )
    if embed is None:
        return None

    embed.color = 0x00FF00 if oper == "accept" else 0xFF0000
    embed.title = "操作已完成" if oper == "accept" else "操作已拒絕"
    return embed


async def request_accept(message: Message, uid: int, is_borrow: bool):
    embed = await accept_or_reject_func(
        oper="accept",
        uid=uid,
        is_borrow=is_borrow,
        embed=message.embeds[0] if len(message.embeds) > 0 else None
    )

    if embed is None:
        return

    await message.edit(
        content="",
        embed=embed,
        view=None
    )


async def request_reject(message: Message, uid: int, is_borrow: bool):
    embed = await accept_or_reject_func(
        oper="reject",
        uid=uid,
        is_borrow=is_borrow,
        embed=message.embeds[0] if len(message.embeds) > 0 else None
    )

    if embed is None:
        return

    await message.edit(
        content="",
        embed=embed,
        view=None
    )
